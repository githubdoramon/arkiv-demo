import { createPublicClient, createWalletClient, ExpirationTime, jsonToPayload, type PublicArkivClient, type WalletArkivClient } from '@arkiv-network/sdk';
import { localhost, tiramisu } from '@arkiv-network/sdk/chains';
import { custom, defineChain, http, type Address, type EIP1193Provider, type Hex, type Transport } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { eq } from '@arkiv-network/sdk/query';
import { APP, lower } from './domain';
import type { Entity, Snapshot } from './types';
import { ensureWalletNetwork, type NetworkProvider } from './walletNetwork';
import { runTransaction, transactionSubmitted } from './feedback';
import { arkivRpcUrl as rpcUrl, isLocalNetwork, networkConfig } from './config';
const chain = defineChain({ ...(isLocalNetwork ? localhost : tiramisu), name: networkConfig.name, nativeCurrency: {name: isLocalNetwork ? 'Test GLM' : 'Golem', symbol: 'GLM', decimals: 18}, rpcUrls: { default: { http: [rpcUrl] } } });
const walletNetwork = { chainId: networkConfig.id, chainName: chain.name, rpcUrl, nativeCurrency: chain.nativeCurrency };
export type WalletMode = 'injected' | 'dev';
// Public Anvil sample keys for disposable local chain 1337 only; never use for real funds.
const devKeys: Record<string, Hex> = {
    author: '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80',
    reviewer: '0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d',
};
function monitoredTransport(base:Transport):Transport {
    return options=>{
        const transport=base(options);
        return {...transport,request:new Proxy(transport.request,{
            async apply(target,thisArg,args){
                const result=await Reflect.apply(target,thisArg,args);
                if(['eth_sendTransaction','eth_sendRawTransaction'].includes(args[0]?.method)&&typeof result==='string'&&/^0x[0-9a-f]{64}$/i.test(result)) transactionSubmitted(result);
                return result;
            },
        })};
    };
}
export function createPublicArkivClient(): PublicArkivClient {
    return createPublicClient({ chain, transport: http(rpcUrl) }) as PublicArkivClient;
}
export async function readDirectSnapshot(): Promise<Snapshot> {
    const client = createPublicArkivClient();
    const [chainId, head] = await Promise.all([client.getChainId(), client.getBlockNumber()]);
    if (chainId !== networkConfig.id)
        throw new Error(`Expected ${networkConfig.name} chain ${networkConfig.id}; RPC reports ${chainId}.`);
    const headBlock = await client.getBlock({ blockNumber: head });
    const result: Entity[] = [];
    const builder = client.select('*').where(eq('app', APP)).atBlock(head).limit(200);
    for await (const e of builder) {
        if (!e.key || !e.creator || !e.owner || !e.createdAt || !e.expiresAt || !e.attributes || !e.payload || !e.creationFlags)
            continue;
        const attrs: Record<string, unknown> = {};
        for (const [name, value] of Object.entries(e.attributes)) {
            attrs[name] = value && typeof value === 'object' && 'value' in value ? (value as {
                value: unknown;
            }).value : value;
        }
        let data: Record<string, unknown> = {};
        try {
            const parsed = e.toJson();
            if (parsed && typeof parsed === 'object')
                data = parsed as Record<string, unknown>;
        }
        catch {
            continue;
        }
        result.push({ key: lower(e.key), creator: lower(e.creator), owner: lower(e.owner), created_at_block: Number(e.createdAt), created_at_timestamp: 0, expires_at_block: Number(e.expiresAt), flags: { readonly: e.creationFlags.readonly, permissionless_extension: e.creationFlags.permissionlessExtension }, attributes: attrs, payload: data });
    }
    const blockNumbers = [...new Set(result.map(e => e.created_at_block))];
    const timestamps = await Promise.all(blockNumbers.map(async (n) => {
        try {
            const block = await client.getBlock({ blockNumber: BigInt(n) });
            return [n, Number(block.timestamp)] as const;
        }
        catch {
            return [n, 0] as const;
        }
    }));
    const timeMap = new Map(timestamps);
    for (const e of result)
        e.created_at_timestamp = timeMap.get(e.created_at_block) ?? 0;
    return { chain_id: chainId, block_number: Number(head), block_timestamp: Number(headBlock.timestamp), evaluation_day: Math.floor(Number(headBlock.timestamp) / 86400), entities: result };
}
export type ConnectedWallet = {
    address: Address;
    mode: WalletMode;
    client: WalletArkivClient;
    signMessage: (message: string) => Promise<Hex>;
};
function injectedProvider() {
    const provider = (window as Window & { ethereum?: EIP1193Provider }).ethereum;
    if (!provider) throw new Error('No browser wallet was found. Install or unlock your wallet, then try again.');
    return provider;
}
export async function ensureConnectedNetwork(wallet: ConnectedWallet) {
    if (wallet.mode === 'injected') await ensureWalletNetwork(injectedProvider() as unknown as NetworkProvider, walletNetwork);
}
export async function connectInjected(): Promise<ConnectedWallet> {
    const provider = injectedProvider();
    const addresses = await provider.request({ method: 'eth_requestAccounts' }) as Address[];
    if (!addresses[0]) throw new Error('The wallet did not return an address.');
    await ensureWalletNetwork(provider as unknown as NetworkProvider, walletNetwork);
    const client = createWalletClient({ account: addresses[0], chain, transport: monitoredTransport(custom(provider)) });
    return {
        address: addresses[0], mode: 'injected', client,
        signMessage: async (message) => {
            await ensureWalletNetwork(provider as unknown as NetworkProvider, walletNetwork);
            return client.signMessage({ account: addresses[0], message });
        },
    };
}
export async function connectDevWallet(which: 'author' | 'reviewer'): Promise<ConnectedWallet> {
    if (!isLocalNetwork || !isLoopbackRpc(rpcUrl))
        throw new Error('Local dev wallets are enabled only when VITE_ARKIV_RPC_URL points to loopback.');
    const publicClient = createPublicArkivClient();
    const chainId = await publicClient.getChainId();
    if (chainId !== 1337)
        throw new Error(`Refusing local dev key: RPC reports chain ${chainId}, expected 1337.`);
    const account = privateKeyToAccount(devKeys[which]);
    const client = createWalletClient({ account, chain, transport: monitoredTransport(http(rpcUrl)) });
    return { address: account.address, mode: 'dev', client, signMessage: (message) => client.signMessage({ account, message }) };
}
function isLoopbackRpc(raw: string) {
    try {
        const host = new URL(raw).hostname.toLowerCase();
        return host === 'localhost' || host === '127.0.0.1' || host === '[::1]' || host === '::1';
    }
    catch {
        return false;
    }
}
export async function createRecord(wallet: ConnectedWallet, kind: string, schema: string, payload: Record<string, unknown>, attributes: Record<string, string | number>, readonly = true) {
    await ensureConnectedNetwork(wallet);
    return runTransaction(({profile:'Save profile','review-revision':'Publish review','review-vote':'Save vote','review-comment':'Add comment'} as Record<string,string>)[kind] || 'Save data',()=>wallet.client.createEntity({ payload: jsonToPayload({ schema, ...payload }), contentType: 'application/json', attributes: { app: APP, kind, ...attributes }, expires: ExpirationTime.fromDays(180), flags: { readonly, permissionlessExtension: true } }));
}
export async function renewRecord(wallet: ConnectedWallet, key: Hex, currentExpiryBlock: number, extraDays = 180) {
    await ensureConnectedNetwork(wallet);
    const target = BigInt(currentExpiryBlock + extraDays * 24 * 60 * 60 / 2);
    return runTransaction('Keep review',()=>wallet.client.extendEntity({ entityKey: key, expires: ExpirationTime.atBlock(target) }));
}

/** Keep the user-visible review and its version history alive in one transaction. */
export async function renewReview(wallet: ConnectedWallet, entities: Entity[], extraDays=180) {
    await ensureConnectedNetwork(wallet);
    const extension=BigInt(extraDays*86400/2);
    return runTransaction('Keep review',()=>wallet.client.executeBatch({extensions:entities.map(entity=>({entityKey:entity.key as Hex,expires:ExpirationTime.atBlock(BigInt(entity.expires_at_block)+extension)}))}));
}
