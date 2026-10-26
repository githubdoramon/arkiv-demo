const network = import.meta.env.VITE_ARKIV_NETWORK || 'local';
if (!['local', 'tiramisu'].includes(network)) throw new Error('Unknown Arkiv network: '+network);
export const isLocalNetwork = network === 'local';
export const networkConfig = isLocalNetwork
  ? {id:1337,name:'Sidequest Local',rpcUrl:'http://127.0.0.1:18547'}
  : {id:7738577,name:'Tiramisu',rpcUrl:'https://rpc.tiramisu.db-chain.testnet.arkiv.network'};
export const arkivRpcUrl = (import.meta.env.VITE_ARKIV_RPC_URL || networkConfig.rpcUrl).trim();
export const reviewAppUrl = import.meta.env.VITE_REVIEW_APP_URL || 'http://127.0.0.1:5173/';
export const portfolioUrl = import.meta.env.VITE_PORTFOLIO_URL || 'http://127.0.0.1:5174/';
export function appLink(base:string,params:Record<string,string>) {
  const url=new URL(base,window.location.href);
  for(const [key,value] of Object.entries(params))url.searchParams.set(key,value);
  return url.href;
}
