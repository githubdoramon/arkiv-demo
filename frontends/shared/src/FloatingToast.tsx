import { useEffect, useState } from 'react';
import { FEEDBACK_EVENT, transactionExplorerUrl, type Feedback } from './feedback';

export function FloatingToast({notice='',error='',onDismiss}:{notice?:string;error?:string;onDismiss?:()=>void}) {
  const [feedback,setFeedback] = useState<Feedback|null>(null);
  useEffect(()=>{
    const receive=(event:Event)=>setFeedback((event as CustomEvent<Feedback>).detail);
    window.addEventListener(FEEDBACK_EVENT,receive);
    return()=>window.removeEventListener(FEEDBACK_EVENT,receive);
  },[]);
  useEffect(()=>{
    if(error) setFeedback({phase:'error',message:error});
    else if(notice) setFeedback({phase:'notice',message:notice});
  },[notice,error]);
  useEffect(()=>{
    if(!feedback || ['wallet','submitted'].includes(feedback.phase)) return;
    const timer=setTimeout(()=>{setFeedback(null);onDismiss?.();},feedback.phase==='error'?12000:8500);
    return()=>clearTimeout(timer);
  },[feedback]);
  if(!feedback)return null;
  const title=feedback.phase==='wallet'?'Confirm in your wallet':feedback.phase==='submitted'?'Transaction pending':feedback.phase==='confirmed'?'Transaction confirmed':feedback.phase==='error'?'Something went wrong':null;
  return <aside key={feedback.phase+':'+(feedback.hash||feedback.message)} className={'floating-toast toast-'+feedback.phase} role={feedback.phase==='error'?'alert':'status'} aria-live="polite">
    <div className="toast-symbol" aria-hidden="true">{feedback.phase==='confirmed'?'✓':feedback.phase==='error'?'!':feedback.phase==='wallet'||feedback.phase==='submitted'?'…':'✓'}</div>
    <div className="toast-copy">{title&&<strong>{title}</strong>}<p>{feedback.message}</p>{feedback.hash&&<a href={transactionExplorerUrl(feedback.hash)} target="_blank" rel="noreferrer">View transaction <span>{feedback.hash.slice(0,8)}…{feedback.hash.slice(-6)}</span></a>}</div>
    <button className="toast-close" aria-label="Dismiss notification" onClick={()=>{setFeedback(null);onDismiss?.();}}>×</button>
  </aside>;
}
