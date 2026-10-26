export type NetworkProvider = {
  request(args: { method: string; params?: unknown[] }): Promise<unknown>;
};

export type WalletNetwork = {
  chainId: number;
  chainName: string;
  rpcUrl: string;
  nativeCurrency: { name: string; symbol: string; decimals: number };
};

function walletErrorCode(error: unknown): number | undefined {
  const value = error as { code?: number; data?: { originalError?: { code?: number } }; cause?: { code?: number } };
  const codes = [value?.code, value?.data?.originalError?.code, value?.cause?.code];
  return codes.includes(4902) ? 4902 : codes.find(code => code !== undefined);
}

/** Ask the wallet to switch, registering the network first only when it is unknown. */
export async function ensureWalletNetwork(provider: NetworkProvider, network: WalletNetwork) {
  const chainId = `0x${network.chainId.toString(16)}`;
  const current = await provider.request({ method: 'eth_chainId' });
  if (Number(current) === network.chainId) return;

  try {
    await provider.request({ method: 'wallet_switchEthereumChain', params: [{ chainId }] });
  } catch (error) {
    if (walletErrorCode(error) !== 4902) throw error;
    await provider.request({
      method: 'wallet_addEthereumChain',
      params: [{ chainId, chainName: network.chainName, rpcUrls: [network.rpcUrl], nativeCurrency: network.nativeCurrency }],
    });
    // Some wallets add a network without selecting it.
    const afterAdding = await provider.request({ method: 'eth_chainId' });
    if (Number(afterAdding) !== network.chainId) {
      await provider.request({ method: 'wallet_switchEthereumChain', params: [{ chainId }] });
    }
  }

  const confirmed = await provider.request({ method: 'eth_chainId' });
  if (Number(confirmed) !== network.chainId) {
    throw new Error('The wallet did not switch networks. Approve the network request and try again.');
  }
}
