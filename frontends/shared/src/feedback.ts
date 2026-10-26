import { appLink, portfolioUrl, isLocalNetwork } from './config';
export type Feedback = {
  phase: 'notice' | 'wallet' | 'submitted' | 'confirmed' | 'error';
  message: string;
  hash?: string;
};
export const FEEDBACK_EVENT = 'sidequest:feedback';
let activeAction = '';

export function emitFeedback(feedback: Feedback) {
  if (typeof window !== 'undefined') window.dispatchEvent(new CustomEvent(FEEDBACK_EVENT, {detail: feedback}));
}

export function transactionSubmitted(hash: string) {
  if (activeAction) emitFeedback({phase:'submitted',message:activeAction,hash});
}

export async function runTransaction<T extends {txHash?: string}>(message: string, action: () => Promise<T>): Promise<T> {
  activeAction = message;
  emitFeedback({phase:'wallet',message});
  try {
    const result = await action();
    emitFeedback({phase:'confirmed',message,hash:result.txHash});
    return result;
  } catch (error) {
    const value = error as {shortMessage?:string;message?:string;code?:number};
    emitFeedback({phase:'error',message:value.code===4001?'Cancelled in your wallet.':value.shortMessage || value.message || 'The transaction could not be completed.'});
    throw error;
  } finally { activeAction = ''; }
}

export function dataExplorerUrl(key: string) {
  return isLocalNetwork ? appLink(portfolioUrl,{entity:key}) : 'https://data.arkiv.network/entity/'+encodeURIComponent(key);
}
export function transactionExplorerUrl(hash: string) {
  return isLocalNetwork ? appLink(portfolioUrl,{tx:hash}) : 'https://tiramisu.explorer.arkiv.network/tx/'+encodeURIComponent(hash);
}
