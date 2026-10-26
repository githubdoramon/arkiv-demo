import React, { FormEvent, useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import gamesFile from '../../../shared/games.json';
import { reviewAppUrl, portfolioUrl, appLink, Atmosphere, DataExplorer, FloatingToast, dataExplorerUrl, daysRemaining, derive, displayScore, formatWallet, lower, readDirectSnapshot, useLibraryMotion, type Derived, type Game, type Review, type Snapshot } from '@sidequest/shared';
import './style.css';

const games=gamesFile as Game[];
const cover=(id:string)=>games.find(game=>game.id===id)?.cover_image || games.find(game=>game.id===id)?.cover_source || '';

function App(){
 const motionRef=useLibraryMotion();
 const initial=new URL(location.href).searchParams.get('wallet')||'';
 const [wallet,setWallet]=useState(initial),[input,setInput]=useState(initial);
 const [snapshot,setSnapshot]=useState<Snapshot|null>(null),[derived,setDerived]=useState<Derived|null>(null);
 const [busy,setBusy]=useState(false),[error,setError]=useState('');
 const fetching=useRef(false);
 const normalized=lower(wallet),profile=derived?.profiles.get(normalized);
 const name=String(profile?.payload.display_name||formatWallet(wallet));
 const reviews=useMemo(()=>derived?.reviews.filter(review=>review.author===normalized).sort((a,b)=>b.revision.created_at_block-a.revision.created_at_block)||[],[derived,normalized]);
 const received=useMemo(()=>derived?.canonicalVotes.filter(vote=>{
  const revision=derived.canonicalRevisions.find(item=>lower(item.key)===lower(vote.payload.target_revision_key));
  return revision&&lower(revision.payload.author)===normalized;
 })||[],[derived,normalized]);

 async function refresh(){
  if(fetching.current)return;
  fetching.current=true;setBusy(true);
  try{const data=await readDirectSnapshot();setSnapshot(data);setDerived(derive(data));setError('');}
  catch{setError('We couldn’t load the latest portfolios. Please try again.');}
  finally{fetching.current=false;setBusy(false);}
 }
 useEffect(()=>{
  void refresh();
  const update=()=>{if(!document.hidden)void refresh();};
  const timer=setInterval(update,10000);
  window.addEventListener('focus',update);document.addEventListener('visibilitychange',update);
  return()=>{clearInterval(timer);window.removeEventListener('focus',update);document.removeEventListener('visibilitychange',update);};
 },[]);
 function selectWallet(address:string){
  setWallet(address);setInput(address);setError('');
  const url=new URL(location.href);url.searchParams.set('wallet',address);history.replaceState({},'',url);
  window.scrollTo({top:0,behavior:'smooth'});void refresh();
 }
 function openPortfolio(event:FormEvent){
  event.preventDefault();
  if(!/^0x[0-9a-fA-F]{40}$/.test(input.trim())){setError('Select a reviewer below, or enter a full wallet address.');return;}
  selectWallet(input.trim());
 }
 const reviewers=useMemo(()=>{
  if(!derived)return[];
  const addresses=new Set([...derived.profiles.keys(),...derived.reviews.map(review=>review.author)]);
  return [...addresses].map(address=>({address,name:String(derived.profiles.get(address)?.payload.display_name||formatWallet(address)),reviews:derived.reviews.filter(review=>review.author===address)})).sort((a,b)=>b.reviews.length-a.reviews.length||a.name.localeCompare(b.name));
 },[derived]);
 const directory=reviewers.filter(person=>(person.name+' '+person.address).toLowerCase().includes(input.toLowerCase().trim()));
 const helpful=received.filter(vote=>vote.payload.value==='helpful').length;
 const initials=name.split(' ').map(part=>part[0]).slice(0,2).join('');

 return <div className="portfolio-shell">
  <FloatingToast error={error} onDismiss={()=>setError('')}/>
  <header className="folio-nav"><a href={reviewAppUrl} className="folio-brand"><span className="folio-mark" aria-hidden="true">S</span>Sidequest</a><nav><a href={reviewAppUrl}>Discover</a><a href={portfolioUrl} aria-current="page">Portfolios</a></nav><button className="refresh" onClick={()=>void refresh()} disabled={busy}>{busy?'Refreshing…':'Refresh'}</button></header>
  <main ref={motionRef}>{!wallet?<section className="folio-empty"><div className="directory-heading"><span className="section-eyebrow">The people behind the reviews</span><h1>Find your kind of player.</h1><p>Explore their reviews. Discover a different point of view.</p></div><form onSubmit={openPortfolio}><input value={input} onChange={event=>setInput(event.target.value)} placeholder="Search reviewers or enter a wallet address" aria-label="Wallet address"/><button className="quest-button">Find reviewer</button></form>
   <div className="reviewer-list">{directory.map((person,index)=><button className="reviewer-card" data-reveal style={{'--reveal-delay':`${(index%3)*65}ms`} as React.CSSProperties} key={person.address} onClick={()=>selectWallet(person.address)}><div className="reviewer-games">{person.reviews.slice(0,3).map(review=><img key={review.root.key} src={cover(review.game_id)} alt="" width="100" height="150" loading="lazy"/>)}</div><div className="reviewer-card-content"><span className="reviewer-avatar" aria-hidden="true">{person.name[0]}</span><div><strong>{person.name}</strong><span>{person.reviews.length} {person.reviews.length===1?'review':'reviews'}</span></div><span className="reviewer-open" aria-hidden="true">↗</span></div></button>)}</div>
   {busy&&!derived&&<p className="loading-copy">Loading reviewers…</p>}{derived&&!directory.length&&<p className="loading-copy">No reviewers match this search yet.</p>}
  </section>:<>
   <section className="folio-hero"><div className="folio-avatar" aria-hidden="true">{initials}</div><div className="folio-intro"><span className="section-eyebrow">Player profile</span><h1>{name}</h1><p className="folio-address">{wallet}</p>{!!profile?.payload.bio&&<p className="folio-bio">{String(profile.payload.bio)}</p>}<div className="folio-stats"><span><b>{reviews.length}</b> reviews</span><span><b>{displayScore(derived?.scores[normalized]||0)}</b> reputation</span><span><b>{helpful}</b> Helpful votes</span></div><div className="profile-links">{profile&&<a className="data-link" href={dataExplorerUrl(profile.key)} target="_blank" rel="noreferrer">View profile data ↗</a>}<a className="data-link" href={appLink(reviewAppUrl,{wallet,edit:'1'})}>Edit profile ↗</a></div></div></section>
   <section className="folio-body"><div className="folio-section-head"><h2>Reviews</h2></div>{!reviews.length?<div className="folio-no-records"><h3>No reviews yet.</h3><p>This player’s reviews will appear here when they publish them.</p></div>:<div className="folio-review-list">{reviews.map(review=><FolioReview key={review.root.key} review={review} snapshot={snapshot!}/>)}</div>}<div className="folio-switch"><span>Find another reviewer</span><form onSubmit={openPortfolio}><input value={input} onChange={event=>setInput(event.target.value)} placeholder="Enter a wallet address" aria-label="Load another wallet"/><button className="quest-button">Open portfolio</button></form></div></section>
  </>}</main><footer className="folio-footer"><span>Sidequest</span><a href={reviewAppUrl}>Explore games</a></footer>
 </div>;
}
function FolioReview({review,snapshot}:{review:Review;snapshot:Snapshot}){
 const game=games.find(item=>item.id===review.game_id),days=daysRemaining(review.expires_at_block,snapshot.block_number);
 const url=appLink(reviewAppUrl,{game:review.game_id});
 return <article className="folio-review" data-reveal><a className="folio-game-cover" href={url}><img src={cover(review.game_id)} alt={(game?.title||review.game_id)+' cover art'} width="600" height="900" loading="lazy"/></a><div className="folio-review-main"><div className="folio-game-line"><span>{review.platform.replaceAll('-',' ')}</span><span>{new Date(review.revision.created_at_timestamp*1000).toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'})}</span>{review.revisions.length>1&&<span>Updated</span>}</div><h3><a href={url}>{game?.title||review.game_id}</a></h3><div className="folio-rating"><span aria-label={(review.rating_half_stars/2)+' out of 5 stars'}>{'★'.repeat(Math.floor(review.rating_half_stars/2))}{review.rating_half_stars%2?'½':''}</span><b>{(review.rating_half_stars/2).toFixed(1)} / 5</b></div><p>{review.text}</p><div className="folio-review-foot"><span>{review.helpful} Helpful</span><span>{review.unhelpful} Unhelpful</span><span>{review.comments.length} comments</span><span>Available for {days} more days</span><a className="data-link" href={dataExplorerUrl(review.revision.key)} target="_blank" rel="noreferrer">View data ↗</a></div></div></article>;
}
function Root(){
 const query=new URL(location.href).searchParams;
 if(query.has('entity')||query.has('tx'))return <><Atmosphere/><DataExplorer entityKey={query.get('entity')} transactionHash={query.get('tx')}/></>;
 return <><Atmosphere/><App/></>;
}
const root = import.meta.hot?.data.root ?? createRoot(document.getElementById('root')!);
if (import.meta.hot) import.meta.hot.data.root = root;
root.render(<React.StrictMode><Root/></React.StrictMode>);
