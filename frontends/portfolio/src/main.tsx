import React, { FormEvent, useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import gamesFile from '../../../shared/games.json';
import { reviewAppUrl, portfolioUrl, appLink, DataExplorer, FloatingToast, dataExplorerUrl, daysRemaining, derive, displayScore, lower, readDirectSnapshot, Icon, platformName, type Derived, type Game, type Review, type Snapshot } from '@sidequest/shared';
import './style.css';

const games=gamesFile as Game[];
const cover=(id:string)=>'/games/'+id+'.jpg';
const playerName=(address:string,derived:Derived|null)=>String(derived?.profiles.get(lower(address))?.payload.display_name||('Player '+address.slice(-4)));

function App(){
 const initial=new URL(location.href).searchParams.get('wallet')||'';
 const [wallet,setWallet]=useState(initial),[input,setInput]=useState('');
 const [snapshot,setSnapshot]=useState<Snapshot|null>(null),[derived,setDerived]=useState<Derived|null>(null);
 const [busy,setBusy]=useState(false),[error,setError]=useState('');
 const fetching=useRef(false);
 const normalized=lower(wallet),profile=derived?.profiles.get(normalized),name=playerName(wallet,derived);
 const reviews=useMemo(()=>derived?.reviews.filter(review=>review.author===normalized).sort((a,b)=>b.revision.created_at_block-a.revision.created_at_block)||[],[derived,normalized]);
 const received=useMemo(()=>derived?.canonicalVotes.filter(vote=>{
  const revision=derived.canonicalRevisions.find(item=>lower(item.key)===lower(vote.payload.target_revision_key));
  return revision&&lower(revision.payload.author)===normalized;
 })||[],[derived,normalized]);
 async function refresh(){
  if(fetching.current)return;
  fetching.current=true;setBusy(true);
  try{const data=await readDirectSnapshot();setSnapshot(data);setDerived(derive(data));setError('');}
  catch{setError('We couldn’t load the latest reviews. Please try again.');}
  finally{fetching.current=false;setBusy(false);}
 }
 useEffect(()=>{
  void refresh();
  const update=()=>{if(!document.hidden)void refresh();};
  const timer=setInterval(update,10000);
  window.addEventListener('focus',update);document.addEventListener('visibilitychange',update);
  const navigate=()=>{setWallet(new URL(location.href).searchParams.get('wallet')||'');setInput('');};
  window.addEventListener('popstate',navigate);
  return()=>{clearInterval(timer);window.removeEventListener('focus',update);document.removeEventListener('visibilitychange',update);window.removeEventListener('popstate',navigate);};
 },[]);
 function selectWallet(address:string){
  setWallet(address);setInput('');setError('');
  const url=new URL(location.href);if(address)url.searchParams.set('wallet',address);else url.searchParams.delete('wallet');history.pushState({},'',url);
  window.scrollTo({top:0,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});void refresh();
 }
 const reviewers=useMemo(()=>{
  if(!derived)return[];
  const addresses=new Set([...derived.profiles.keys(),...derived.reviews.map(review=>review.author)]);
  return [...addresses].map(address=>({address,name:playerName(address,derived),reviews:derived.reviews.filter(review=>review.author===address)})).sort((a,b)=>b.reviews.length-a.reviews.length||a.name.localeCompare(b.name));
 },[derived]);
 const directory=reviewers.filter(person=>(person.name+' '+person.address).toLowerCase().includes(input.toLowerCase().trim()));
 function openPortfolio(event:FormEvent){
  event.preventDefault();
  if(/^0x[0-9a-fA-F]{40}$/.test(input.trim())){selectWallet(input.trim());return;}
  if(directory.length===1){selectWallet(directory[0].address);return;}
  setError('Choose a reviewer below, or search by their name.');
 }
 const helpful=received.filter(vote=>vote.payload.value==='helpful').length;
 const initials=name.split(' ').map(part=>part[0]).slice(0,2).join('');
 const bio=String(profile?.payload.bio||'');
 const searchForm=<form className="reviewer-search" onSubmit={openPortfolio}><label><span className="sr-only">Find a reviewer by name or account address</span><Icon name="search"/><input type="search" value={input} onChange={event=>setInput(event.target.value)} placeholder="Find a reviewer"/></label></form>;
 return <div className="portfolio-shell">
  <FloatingToast error={error} onDismiss={()=>setError('')}/>
  <header className="folio-nav"><a href={portfolioUrl} onClick={event=>{event.preventDefault();selectWallet('');}} className="folio-brand">Afterword<span aria-hidden="true"/></a><nav aria-label="Main navigation"><a href={portfolioUrl} onClick={event=>{event.preventDefault();selectWallet('');}} aria-current={!wallet?'page':undefined}>Reviewers</a><a href={reviewAppUrl}>Explore games <Icon name="external"/></a></nav><button className="refresh" onClick={()=>void refresh()} disabled={busy}><Icon name="refresh" className={busy?'is-refreshing':''}/><span>{busy?'Refreshing…':'Refresh'}</span></button></header>
  <main>{!wallet?<section className="reviewer-directory"><div className="directory-opening"><h1>More than<br/> a score.</h1><div><p>Meet the players behind the reviews.<br/> Read what stayed with them.</p>{searchForm}</div></div>
   <div className="directory-list">{directory.map(person=><a className="directory-person" href={appLink(portfolioUrl,{wallet:person.address})} onClick={event=>{event.preventDefault();selectWallet(person.address);}} key={person.address}><div className="directory-identity"><span className="directory-monogram" aria-hidden="true">{person.name.split(' ').map(p=>p[0]).slice(0,2).join('')}</span><div><h2>{person.name}</h2><p>{String(derived?.profiles.get(person.address)?.payload.bio||'A different perspective on the games we play.')}</p><small>{person.reviews.length} {person.reviews.length===1?'review':'reviews'}</small></div></div><div className="directory-covers" aria-hidden="true">{person.reviews.slice(0,3).map(review=><img key={review.root.key} src={cover(review.game_id)} alt="" width="600" height="900" loading="lazy"/>)}</div><Icon name="arrow"/></a>)}</div>
   {busy&&!derived&&<p className="loading-copy" role="status">Finding the people behind the reviews…</p>}{derived&&!directory.length&&<div className="folio-no-records"><h2>No reviewers found.</h2><p>Try another name, or paste a full account address into the search.</p><button onClick={()=>setInput('')}>Show all reviewers</button></div>}
  </section>:<div className="profile-layout">
   <aside className="author-rail" aria-label="About the reviewer"><div className="author-monogram" aria-hidden="true">{initials}</div>{bio&&<p className="author-bio">{bio}</p>}<dl className="author-stats"><div><dt>Reviews</dt><dd>{reviews.length}</dd></div><div><dt>Reputation</dt><dd>{displayScore(derived?.scores[normalized]||0)}</dd></div><div><dt>Helpful votes</dt><dd>{helpful}</dd></div></dl><div className="author-links">{profile&&<a href={dataExplorerUrl(profile.key)} target="_blank" rel="noreferrer">Profile source <Icon name="external"/></a>}<a href={appLink(reviewAppUrl,{wallet,edit:'1'})}>Edit profile <Icon name="external"/></a><button onClick={()=>selectWallet('')}><Icon name="back"/> All reviewers</button></div><details className="account-details"><summary>Account details</summary><code>{wallet}</code></details></aside>
   <section className="reading-column"><header className="author-heading"><h1>{name}</h1><p>{reviews.length?`A life in games. ${reviews.length} ${reviews.length===1?'review':'reviews'}, in their own words.`:'A life in games, in their own words.'}</p></header>
    {busy&&!derived&&<p className="loading-copy" role="status">Loading this player’s reviews…</p>}
    {!reviews.length&&derived?<div className="folio-no-records"><h2>The first page is still unwritten.</h2><p>This player’s reviews will appear here when they publish them.</p></div>:<div className="folio-review-list">{reviews.map(review=><FolioReview key={review.root.key} review={review} snapshot={snapshot!}/>)}</div>}
   </section>
   <aside className="review-index" aria-label="Review index"><h2>All reviews <span>({reviews.length})</span></h2>{reviews.map(review=><a key={review.root.key} href={'#review-'+review.root.key}><img src={cover(review.game_id)} alt="" width="600" height="900" loading="lazy"/><span><strong>{games.find(g=>g.id===review.game_id)?.title||review.game_id}</strong><small>{platformName(review.platform)}</small><b>{(review.rating_half_stars/2).toFixed(1)} <span>/ 5</span></b></span></a>)}</aside>
  </div>}</main><footer className="folio-footer"><a className="footer-wordmark" href={portfolioUrl}>Afterword</a><span>Games end. The conversation carries on.</span><a href={reviewAppUrl}>Find your next game <Icon name="external"/></a></footer>
 </div>;
}
function FolioReview({review,snapshot}:{review:Review;snapshot:Snapshot}){
 const game=games.find(item=>item.id===review.game_id),days=daysRemaining(review.expires_at_block,snapshot.block_number);
 const url=appLink(reviewAppUrl,{game:review.game_id});
 return <article className="folio-review" id={'review-'+review.root.key}><a className="folio-game-cover" href={url}><img src={cover(review.game_id)} alt={(game?.title||review.game_id)+' cover art'} width="600" height="900" loading="lazy"/></a><div className="folio-review-main"><div className="folio-game-line"><span>{platformName(review.platform)}</span><time dateTime={new Date(review.revision.created_at_timestamp*1000).toISOString()}>{new Date(review.revision.created_at_timestamp*1000).toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'})}</time>{review.revisions.length>1&&<span>Updated</span>}</div><h2><a href={url}>{game?.title||review.game_id}</a></h2><div className="folio-rating"><span className="rating-stars" aria-hidden="true">{'★'.repeat(Math.floor(review.rating_half_stars/2))}{review.rating_half_stars%2?'½':''}</span><b>{(review.rating_half_stars/2).toFixed(1)} <span>/ 5</span></b></div><p>{review.text}</p><div className="folio-review-meta"><span>{review.helpful} Helpful</span><span>{review.unhelpful} Unhelpful</span><span>{review.comments.length} {review.comments.length===1?'comment':'comments'}</span><span>Expires in {days} days</span></div><div className="folio-review-links"><a href={url}>Read on Sidequest <Icon name="external"/></a><a className="data-link" href={dataExplorerUrl(review.revision.key)} target="_blank" rel="noreferrer">View source <Icon name="external"/></a></div></div></article>;
}
function Root(){
 const query=new URL(location.href).searchParams;
 if(query.has('entity')||query.has('tx'))return <DataExplorer entityKey={query.get('entity')} transactionHash={query.get('tx')}/>;
 return <App/>;
}
const root = import.meta.hot?.data.root ?? createRoot(document.getElementById('root')!);
if (import.meta.hot) import.meta.hot.data.root = root;
root.render(<React.StrictMode><Root/></React.StrictMode>);
