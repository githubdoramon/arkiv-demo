import { useEffect, useState } from 'react';
import { Icon } from './Icons';
import { FEEDBACK_EVENT, transactionExplorerUrl, type Feedback } from './feedback';

function actionCopy(feedback:Feedback) {
  const actions:Record<string,[string,string,string]>={
    'Publish review':['Approve publishing in your wallet.','Your review is being published.','Your review is live.'],
    'Save profile':['Approve your profile changes in your wallet.','Updating your profile…','Your profile has been updated.'],
    'Save vote':['Approve your feedback in your wallet.','Saving your feedback…','Thanks. Your feedback has been saved.'],
    'Add comment':['Approve your comment in your wallet.','Posting your comment…','Your comment has been posted.'],
    'Keep review':['Approve extending your review’s lifetime in your wallet.','Extending your review’s lifetime…','Your review’s lifetime has been extended.'],
  };
  const index=feedback.phase==='wallet'?0:feedback.phase==='submitted'?1:feedback.phase==='confirmed'?2:-1;
  return index===-1?feedback.message:actions[feedback.message]?.[index]||feedback.message;
}

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
  const title=feedback.phase==='wallet'?'Approve your change':feedback.phase==='submitted'?'Saving your change…':feedback.phase==='confirmed'?'All saved':feedback.phase==='error'?'Something went wrong':null;
  return <aside key={feedback.phase+':'+(feedback.hash||feedback.message)} className={'floating-toast toast-'+feedback.phase} role={feedback.phase==='error'?'alert':'status'} aria-live="polite">
    <div className="toast-symbol" aria-hidden="true"><Icon name={feedback.phase==='error'?'alert':feedback.phase==='wallet'||feedback.phase==='submitted'?'pending':'check'}/></div>
    <div className="toast-copy">{title&&<strong>{title}</strong>}<p>{actionCopy(feedback)}</p>{feedback.hash&&<a href={transactionExplorerUrl(feedback.hash)} target="_blank" rel="noreferrer">View confirmation <span>{feedback.hash.slice(0,8)}…{feedback.hash.slice(-6)}</span></a>}</div>
    <button className="toast-close" aria-label="Dismiss notification" onClick={()=>{setFeedback(null);onDismiss?.();}}><Icon name="close"/></button>
  </aside>;
}
