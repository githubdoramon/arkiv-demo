import assert from 'node:assert/strict';
import { ensureWalletNetwork, type NetworkProvider } from '../shared/src/walletNetwork';

const config = {chainId:1337,chainName:'Sidequest Local',rpcUrl:'http://127.0.0.1:18547',nativeCurrency:{name:'Test GLM',symbol:'GLM',decimals:18}};

function wallet({current='0x1',unknown=false,selectOnAdd=false,reject=false,refuseSwitch=false,wrapped=false}={}) {
  const calls: Array<{method:string;params?:unknown[]}> = [];
  let chain=current, added=!unknown;
  const provider:NetworkProvider={async request(args){
    calls.push(args);
    if(args.method==='eth_chainId') return chain;
    if(args.method==='wallet_switchEthereumChain') {
      if(reject) throw Object.assign(new Error('User rejected'),{code:4001});
      if(!added) throw wrapped ? {code:-32603,data:{originalError:{code:4902}}} : {code:4902};
      if(!refuseSwitch) chain='0x539';
      return null;
    }
    if(args.method==='wallet_addEthereumChain') {added=true;if(selectOnAdd)chain='0x539';return null;}
    throw new Error('Unexpected method '+args.method);
  }};
  return {provider,calls};
}

const correct=wallet({current:'0x539'});
await ensureWalletNetwork(correct.provider,config);
assert.deepEqual(correct.calls.map(c=>c.method),['eth_chainId']);

const known=wallet();
await ensureWalletNetwork(known.provider,config);
assert.deepEqual(known.calls.map(c=>c.method),['eth_chainId','wallet_switchEthereumChain','eth_chainId']);

for(const selectOnAdd of [false,true]) {
  const unknown=wallet({unknown:true,selectOnAdd});
  await ensureWalletNetwork(unknown.provider,config);
  const added=unknown.calls.find(c=>c.method==='wallet_addEthereumChain')!;
  assert.deepEqual(added.params,[{chainId:'0x539',chainName:'Sidequest Local',rpcUrls:['http://127.0.0.1:18547'],nativeCurrency:config.nativeCurrency}]);
  assert.equal(unknown.calls.filter(c=>c.method==='wallet_switchEthereumChain').length,selectOnAdd?1:2);
}

const wrapped=wallet({unknown:true,wrapped:true});
await ensureWalletNetwork(wrapped.provider,config);
assert.ok(wrapped.calls.some(c=>c.method==='wallet_addEthereumChain'));

const rejected=wallet({reject:true});
await assert.rejects(ensureWalletNetwork(rejected.provider,config),{code:4001});
assert.ok(!rejected.calls.some(c=>c.method==='wallet_addEthereumChain'));

const refused=wallet({refuseSwitch:true});
await assert.rejects(ensureWalletNetwork(refused.provider,config),/did not switch/);
console.log('Wallet network checks passed: existing network, switch, add, switch after add, wrapped errors and cancellation.');
