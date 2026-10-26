import React, { FormEvent, useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import gamesFile from '../../../shared/games.json';
import { daysRemaining, derive, displayScore, formatWallet, lower, starText, type ConnectedWallet, type Derived, type Entity, type Game, type Review, type Snapshot, connectDevWallet, connectInjected, createPublicArkivClient, renewReview } from '@sidequest/shared';
import { loadCatalog, loadHiddenKeys, loadSnapshot, moderateEntity, submitReport, publishComment, publishProfile, publishReview, publishVote } from '@sidequest/shared';
import { Atmosphere, FloatingToast, dataExplorerUrl, useLibraryMotion, isLocalNetwork, reviewAppUrl, portfolioUrl, appLink } from '@sidequest/shared';
import './style.css';
const fallbackGames = gamesFile as Game[];
function go(params: Record<string, string | undefined>) { const url = new URL(location.href); for (const [k, v] of Object.entries(params)) {
    if (v)
        url.searchParams.set(k, v);
    else
        url.searchParams.delete(k);
} history.pushState({}, '', url); window.dispatchEvent(new PopStateEvent('popstate')); window.scrollTo({ top: 0, behavior: 'smooth' }); }
function useRoute() { const [route, setRoute] = useState(() => new URL(location.href).searchParams); useEffect(() => { const update = () => setRoute(new URL(location.href).searchParams); window.addEventListener('popstate', update); return () => window.removeEventListener('popstate', update); }, []); return route; }
function Cover({game,large=false}:{game:Game;large?:boolean}) {
 return <img className={'cover '+(large?'cover-large':'')} src={game.cover_image || game.cover_source || '/games/'+game.id+'.jpg'} alt={game.title+' cover art'} loading={large?'eager':'lazy'} width="600" height="900"/>;
}
function Header({wallet,onConnect,onDev,onDisconnect}:{wallet:ConnectedWallet|null;onConnect:()=>void;onDev:(name:'author'|'reviewer')=>void;onDisconnect:()=>void}) {
 const [menu,setMenu]=useState(false);
 return <header className="topbar"><button className="brand" onClick={()=>go({game:undefined,wallet:undefined})} aria-label="Sidequest home"><span className="brand-mark" aria-hidden="true">S</span><span>Sidequest</span></button><nav><button onClick={()=>go({game:undefined,wallet:undefined})}>Discover</button><a href={portfolioUrl} target="_blank" rel="noreferrer">Portfolios</a></nav><div className="top-actions">{wallet?<div className="wallet-chip"><button onClick={()=>go({wallet:wallet.address,game:undefined})} aria-label="My profile">My profile <small>{formatWallet(wallet.address)}</small></button><button className="disconnect" onClick={onDisconnect} aria-label="Disconnect wallet">×</button></div>:<div className="connect-wrap"><button className="connect-btn" onClick={()=>setMenu(v=>!v)} aria-expanded={menu}>Connect wallet</button>{menu&&<div className="connect-menu"><button onClick={()=>{setMenu(false);onConnect();}}>Browser wallet</button>{isLocalNetwork&&<><button onClick={()=>{setMenu(false);onDev('author');}}>Local dev · Reviewer 01</button><button onClick={()=>{setMenu(false);onDev('reviewer');}}>Local dev · Reviewer 02</button></>}</div>}</div>}</div></header>;
}
function App() {
    const motionRef = useLibraryMotion();
    const route = useRoute(), [games, setGames] = useState<Game[]>(fallbackGames), [snapshot, setSnapshot] = useState<Snapshot | null>(null), [derived, setDerived] = useState<Derived | null>(null), [hidden, setHidden] = useState<string[]>([]), [wallet, setWallet] = useState<ConnectedWallet | null>(null), [loading, setLoading] = useState(true), [apiError, setApiError] = useState(''), [actionError, setActionError] = useState(''), [notice, setNotice] = useState(''), [search, setSearch] = useState(''), [platformFilter, setPlatformFilter] = useState('all'), [genreFilter, setGenreFilter] = useState('all');
    const gameId = route.get('game'), profileWallet = route.get('wallet');
    async function refresh() { setLoading(true); try {
        const snap = await loadSnapshot();
        setSnapshot(snap);
        setDerived(derive(snap));
        setApiError('');
        try {
            setHidden(await loadHiddenKeys());
        }
        catch {
            setHidden([]);
        }
    }
    catch (e) {
        setApiError(e instanceof Error ? e.message : 'Could not reach the local API.');
    }
    finally {
        setLoading(false);
    } }
    useEffect(() => { void refresh(); void loadCatalog().then(setGames).catch(() => { }); const timer = window.setInterval(() => void refresh(), 20000); return () => clearInterval(timer); }, []);
    const activeReviews = useMemo(() => derived?.reviews.filter(r => !hidden.includes(lower(r.root.key)) && !hidden.includes(lower(r.revision.key))) ?? [], [derived, hidden]);
    const connect = async (fn: () => Promise<ConnectedWallet>) => { try {
        setActionError('');
        setWallet(await fn());
        setNotice('Wallet connected.');
    }
    catch (e) {
        setActionError(e instanceof Error ? e.message : String(e));
    } };
    const visibleGames = games.filter(g => { const hay = [g.title, g.summary, ...g.genres, ...g.platforms].join(' ').toLowerCase(); return hay.includes(search.toLowerCase()) && (genreFilter === 'all' || g.genres.includes(genreFilter)) && (platformFilter === 'all' || g.platforms.includes(platformFilter)); });
    const chosenGame = games.find(g => g.id === gameId), profileReviews = profileWallet ? activeReviews.filter(r => r.author === lower(profileWallet)) : [];
    const genres = [...new Set(games.flatMap(g => g.genres))].sort();
    return <><Atmosphere/><Header wallet={wallet} onConnect={() => connect(connectInjected)} onDev={which => connect(() => connectDevWallet(which))} onDisconnect={() => setWallet(null)}/>
 <FloatingToast notice={notice} error={actionError||apiError} onDismiss={()=>{setNotice('');setActionError('');}}/>
 <main className="page-shell" ref={motionRef}>
 {profileWallet ? <ProfileView wallet={profileWallet} connectedWallet={wallet} onRefresh={refresh} onError={setActionError} reviews={profileReviews} derived={derived} games={games} snapshot={snapshot} back={() => go({ wallet: undefined })}/> : chosenGame ? <GameView key={chosenGame.id} game={chosenGame} reviews={activeReviews.filter(r => r.game_id === chosenGame.id)} derived={derived} snapshot={snapshot} wallet={wallet} onRefresh={refresh} onError={setActionError} onNotice={setNotice}/> : <>
  <section className="hero"><div className="discover-intro"><h1>Discover your next game.</h1><p>Reviews from players. Wherever you play.</p></div><div className="featured-game" data-art-depth><img src={games.find(game=>game.id==='hades')?.hero_image || games.find(game=>game.id==='hades')?.cover_image || ''} alt="Hades artwork" width="1920" height="620" fetchPriority="high"/><div className="featured-copy"><span>In the spotlight</span><h2>Hades</h2><p>One more run. A different story every time.</p><button className="primary-btn" onClick={()=>go({game:'hades'})}>Explore game <span aria-hidden="true">↗</span></button></div></div></section>
  <section className="catalog-section"><div className="section-heading"><h2>Explore games</h2><span className="section-count">{visibleGames.length} games</span></div><div className="filters"><label className="search-box"><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search games, genres, platforms…" aria-label="Search catalog"/></label><label><span className="sr-only">Filter by genre</span><span className="select-control"><select value={genreFilter} onChange={e => setGenreFilter(e.target.value)}><option value="all">All genres</option>{genres.map(g => <option key={g}>{g}</option>)}</select></span></label><label><span className="sr-only">Filter by platform</span><span className="select-control"><select value={platformFilter} onChange={e => setPlatformFilter(e.target.value)}><option value="all">All platforms</option>{[...new Set(games.flatMap(g => g.platforms))].sort().map(p => <option key={p} value={p}>{p.replaceAll('-', ' ')}</option>)}</select></span></label></div>
  {loading && !snapshot ? <div className="loading-state">Loading reviews…</div> : null}
  {visibleGames.length ? <div className="game-grid">{visibleGames.map((game, i) => { const reviews = activeReviews.filter(r => r.game_id === game.id), avg = reviews.length ? reviews.reduce((s, r) => s + r.rating_half_stars, 0) / reviews.length / 2 : null; return <button className="game-card" data-reveal style={{'--reveal-delay':`${(i%5)*45}ms`} as React.CSSProperties} key={game.id} onClick={() => go({ game: game.id })}><div className="card-cover"><Cover game={game}/></div><div className="card-meta"><div><span className="card-year">{game.year}</span><h3>{game.title}</h3></div></div><div className="card-foot"><span>{game.genres.slice(0, 2).join(' · ')}</span><span className="card-rating">{avg ? `★ ${avg.toFixed(1)}` : 'No ratings'} <small>{reviews.length} {reviews.length===1?'review':'reviews'}</small></span></div></button>; })}</div> : <div className="empty-state"><h3>No games found.</h3><p>Try another search or change a filter.</p><button onClick={() => { setSearch(''); setGenreFilter('all'); setPlatformFilter('all'); }}>Reset filters</button></div>}
 </section><footer className="site-footer"><span>Sidequest</span><span>Game reviews from players.</span></footer>{route.get('admin')==='1'&&<ModerationPanel hidden={hidden} onChanged={refresh} onError={setActionError} onNotice={setNotice}/>}</>}
 </main></>;
}
function ModerationPanel({ hidden, onChanged, onError, onNotice }: {
    hidden: string[];
    onChanged: () => Promise<void>;
    onError: (v: string) => void;
    onNotice: (v: string) => void;
}) { const [open, setOpen] = useState(false), [token, setToken] = useState(''), [key, setKey] = useState(''), [reason, setReason] = useState('Reviewed by local operator'), [busy, setBusy] = useState(false); async function update(entityKey: string, isHidden: boolean) { if (!token.trim()) {
    onError('Enter the server-side MODERATOR_TOKEN to change public visibility.');
    return;
} if (!/^0x[0-9a-fA-F]{64}$/.test(entityKey)) {
    onError('Enter a valid 32-byte Arkiv entity key.');
    return;
} setBusy(true); try {
    await moderateEntity(entityKey.toLowerCase(), isHidden, reason.trim(), token);
    onNotice(isHidden ? 'Entity hidden from public app display.' : 'Entity restored to public app display.');
    setKey('');
    await onChanged();
}
catch (e) {
    onError(e instanceof Error ? e.message : String(e));
}
finally {
    setBusy(false);
} } return <section className="moderator"><button className="moderator-toggle" onClick={() => setOpen(v => !v)}>{open ? '−' : '+'} Local operator visibility controls <span>{hidden.length} hidden records</span></button>{open && <div className="moderator-body"><p>Operator token stays in this tab and is sent only to the local API. Visibility does not rewrite Arkiv records or reputation.</p><label>MODERATOR_TOKEN<input type="password" value={token} onChange={e => setToken(e.target.value)} autoComplete="off" placeholder="Enter configured server token"/></label><form onSubmit={e => { e.preventDefault(); void update(key, true); }}><label>Entity key<input value={key} onChange={e => setKey(e.target.value)} placeholder="0x + 64 hex characters"/></label><label>Reason<input maxLength={200} value={reason} onChange={e => setReason(e.target.value)}/></label><button disabled={busy}>{busy ? 'Saving…' : 'Hide record'}</button></form>{hidden.length > 0 && <div className="hidden-list"><b>Hidden keys</b>{hidden.map(k => <div key={k}><code>{k}</code><button disabled={busy} onClick={() => void update(k, false)}>Unhide</button></div>)}</div>}</div>}</section>; }
function ProfileView({wallet,connectedWallet,onRefresh,onError,reviews,derived,games,snapshot,back}:{wallet:string;connectedWallet:ConnectedWallet|null;onRefresh:()=>Promise<void>;onError:(message:string)=>void;reviews:Review[];derived:Derived|null;games:Game[];snapshot:Snapshot|null;back:()=>void}) {
 const profile=derived?.profiles.get(lower(wallet));
 const display=String(profile?.payload.display_name||formatWallet(wallet));
 const own=lower(connectedWallet?.address)===lower(wallet);
 const [editing,setEditing]=useState(new URL(location.href).searchParams.get('edit')==='1');
 const [name,setName]=useState(''),[bio,setBio]=useState(''),[saving,setSaving]=useState(false);
 useEffect(()=>{setName(String(profile?.payload.display_name||''));setBio(String(profile?.payload.bio||''));},[profile?.key,profile?.payload.display_name,profile?.payload.bio]);
 async function save(event:FormEvent){
  event.preventDefault();if(!connectedWallet||!own||!snapshot)return;
  setSaving(true);onError('');
  try{await publishProfile(connectedWallet,snapshot,name,bio);await onRefresh();setEditing(false);}catch(error){onError(error instanceof Error?error.message:String(error));}finally{setSaving(false);}
 }
 return <section className="detail-page profile-page"><button className="back-link" onClick={back}>← Discover games</button>
  <div className="profile-hero"><div className="profile-avatar">{display[0]?.toUpperCase()}</div><div><p className="eyebrow">Player profile</p><h1>{display}</h1><p className="wallet-address">{wallet}</p>{!!profile?.payload.bio&&<p className="profile-bio">{String(profile.payload.bio)}</p>}<div className="profile-metrics"><span><b>{reviews.length}</b> reviews</span><span><b>{displayScore(derived?.scores[lower(wallet)]||0)}</b> reputation</span></div><div className="profile-links"><a className="portfolio-link" href={appLink(portfolioUrl,{wallet})} target="_blank" rel="noreferrer">Open portfolio ↗</a>{profile&&<a className="data-link" href={dataExplorerUrl(profile.key)} target="_blank" rel="noreferrer">View profile data ↗</a>}{own&&<button className="secondary-btn" onClick={()=>setEditing(value=>!value)}>{profile?'Edit profile':'Create profile'}</button>}</div></div></div>
  {!own&&editing&&<p className="profile-connect-hint">Connect this wallet to edit its profile.</p>}
  {own&&editing&&<form className="profile-editor" onSubmit={save}><div className="write-panel-heading"><h2>{profile?'Edit profile':'Create your profile'}</h2><button type="button" className="close-btn" aria-label="Close profile editor" onClick={()=>setEditing(false)}>×</button></div><label>Display name<input value={name} onChange={event=>setName(event.target.value)} maxLength={48} required placeholder="How other players know you"/></label><label>Bio<textarea value={bio} onChange={event=>setBio(event.target.value)} maxLength={280} rows={3} placeholder="What do you like to play?"/><small>{bio.length}/280</small></label><div className="profile-editor-actions"><span>You’ll confirm this change in your wallet.</span><button className="primary-btn" disabled={saving||!name.trim()}>{saving?'Saving…':'Save profile'}</button></div></form>}
  <div className="section-heading compact"><h2>Reviews</h2></div><div className="review-list">{reviews.map(review=><ReviewCard key={review.root.key} review={review} derived={derived} games={games} wallet={connectedWallet} snapshot={snapshot} onRefresh={onRefresh} onError={onError} onNotice={()=>{}} compact/>)}{!reviews.length&&<div className="empty-state"><h3>No reviews yet.</h3><p>Reviews will appear here when this player publishes them.</p></div>}</div>
 </section>;
}
function GameView({ game, reviews, derived, snapshot, wallet, onRefresh, onError, onNotice }: {
    game: Game;
    reviews: Review[];
    derived: Derived | null;
    snapshot: Snapshot | null;
    wallet: ConnectedWallet | null;
    onRefresh: () => Promise<void>;
    onError: (v: string) => void;
    onNotice: (v: string) => void;
}) {
    const [platform, setPlatform] = useState('all'), [sort, setSort] = useState<'latest' | 'rating'>('latest'), [showForm, setShowForm] = useState(false), [rating, setRating] = useState(8), [text, setText] = useState(''), [writing, setWriting] = useState(false);
    const owned = reviews.filter(r => r.author === lower(wallet?.address || '')), personal = platform === 'all' ? owned[0] : owned.find(r => r.platform === platform), available = game.platforms;
    const filtered = reviews.filter(r => platform === 'all' || r.platform === platform).sort((a, b) => sort === 'latest' ? b.revision.created_at_block - a.revision.created_at_block : b.rating_half_stars - a.rating_half_stars);
    const average = reviews.length ? reviews.reduce((s, r) => s + r.rating_half_stars, 0) / reviews.length / 2 : 0;
    useEffect(() => { if (personal) {
        setRating(personal.rating_half_stars);
        setText(personal.text);
    }
    else {
        setRating(8);
        setText('');
    } }, [personal?.revision.key]);
    async function submit(e: FormEvent) { e.preventDefault(); if (!wallet || !snapshot)
        return; setWriting(true); onError(''); try {
        await publishReview(wallet, snapshot, game, platform === 'all' ? (available[0] || 'pc') : platform, rating, text, personal);
        setShowForm(false);
        await onRefresh();
    }
    catch (err) {
        onError(err instanceof Error ? err.message : String(err));
    }
    finally {
        setWriting(false);
    } }
    return <section className="detail-page"><button className="back-link" onClick={() => go({ game: undefined })}>← All games</button><div className="game-detail-hero" data-art-depth style={{'--game-backdrop':`url("${game.hero_image || game.cover_image || game.cover_source || ''}")`} as React.CSSProperties}><Cover game={game} large/><div className="game-detail-copy"><p className="eyebrow">{game.year} · {game.genres.join(' / ')}</p><h1>{game.title}</h1><p>{game.summary}</p><div className="detail-platforms">{game.platforms.map(p => <button className={platform === p ? 'selected' : ''} key={p} onClick={() => setPlatform(platform === p ? 'all' : p)}>{p.replaceAll('-', ' ')}</button>)}</div><div className="rating-summary">{reviews.length ? <><strong>★ {average.toFixed(1)}</strong><span>from {reviews.length} player {reviews.length === 1 ? 'review' : 'reviews'}</span></> : <span>No reviews yet. Your note could start the conversation.</span>}</div></div></div>
 <div className="review-toolbar"><div><h2>{platform === 'all' ? 'Player reviews' : platform.replaceAll('-', ' ')}</h2></div><div className="review-controls"><label><span>Platform</span><span className="select-control"><select value={platform} onChange={e => setPlatform(e.target.value)}><option value="all">All platforms</option>{available.map(p => <option value={p} key={p}>{p.replaceAll('-', ' ')}</option>)}</select></span></label><label><span>Order</span><span className="select-control"><select value={sort} onChange={e => setSort(e.target.value as 'latest' | 'rating')}><option value="latest">Latest first</option><option value="rating">Highest rated</option></select></span></label><button className="primary-btn" onClick={() => { if (!wallet) {
        onError('Connect a wallet before writing a review.');
        return;
    } setShowForm(v => !v); }}>{personal ? 'Edit your review' : 'Write a review'}</button></div></div>
 {showForm && <form className="write-panel" onSubmit={submit}><div className="write-panel-heading"><div><p className="eyebrow">{personal ? 'REVISION ' + (personal.revisions.length + 1) : 'New review'}</p><h3>Write your review</h3></div><button type="button" className="close-btn" onClick={() => setShowForm(false)}>×</button></div><div className="write-grid"><label>Platform<span className="select-control"><select value={platform === 'all' ? (personal?.platform || available[0]) : platform} onChange={e => setPlatform(e.target.value)}>{available.map(p => <option value={p} key={p}>{p.replaceAll('-', ' ')}</option>)}</select></span></label><fieldset className="rating-choice"><legend>Your rating <b>{starText(rating)}</b></legend><div className="star-picker" role="radiogroup" aria-label="Rating" onKeyDown={event=>{const delta=event.key==='ArrowRight'||event.key==='ArrowUp'?1:event.key==='ArrowLeft'||event.key==='ArrowDown'?-1:0;if(delta){event.preventDefault();const group=event.currentTarget;setRating(value=>Math.max(2,Math.min(10,value+delta)));requestAnimationFrame(()=>group.querySelector<HTMLButtonElement>('[aria-checked="true"]')?.focus());}}}>{Array.from({length:5},(_,index)=>{const full=index*2+2,half=full-1;return <span className="star-item" key={index}><span className="star-art" aria-hidden="true" style={{'--fill':rating>=full?'100%':rating===half?'50%':'0%'} as React.CSSProperties}>★</span>{index>0&&<button type="button" role="radio" aria-checked={rating===half} tabIndex={rating===half?0:-1} aria-label={`${half/2} stars`} className="star-hit star-half" onClick={()=>setRating(half)}/>}<button type="button" role="radio" aria-checked={rating===full} tabIndex={rating===full?0:-1} aria-label={`${full/2} ${full===2?'star':'stars'}`} className={'star-hit '+(index===0?'star-whole':'star-full')} onClick={()=>setRating(full)}/></span>})}</div></fieldset><label className="wide">Your review<textarea aria-label="Your review" minLength={10} maxLength={2000} required value={text} onChange={e => setText(e.target.value)} placeholder="What stayed with you after the credits? Keep it spoiler-aware."/><small>{text.length}/2000 · Minimum 10 characters</small></label></div><div className="write-actions"><span>{personal ? 'Earlier feedback stays with the original version.' : 'You’ll confirm this review in your wallet.'}</span><button className="primary-btn" disabled={writing || !snapshot}>{writing ? 'Publishing…' : 'Publish review'}</button></div></form>}
 {wallet&&!derived?.profiles.has(lower(wallet.address))&&<div className="profile-nudge"><span>Add a name and bio so other players can find you.</span><button onClick={()=>go({wallet:wallet.address,game:undefined,edit:'1'})}>Create profile</button></div>}
 <div className="review-list">{filtered.map(r => <ReviewCard key={r.root.key} review={r} derived={derived} games={[game]} wallet={wallet} snapshot={snapshot} onRefresh={onRefresh} onError={onError} onNotice={onNotice}/>)}</div>{!filtered.length && <div className="empty-state"><h3>No reviews yet.</h3><p>Played this game? Share what you thought.</p><button onClick={() => setShowForm(true)}>Write a review</button></div>}</section>;
}
function ReviewCard({ review: r, derived, games, wallet, snapshot, onRefresh, onError, onNotice, compact = false }: {
    review: Review;
    derived: Derived | null;
    games: Game[];
    wallet: ConnectedWallet | null;
    snapshot: Snapshot | null;
    onRefresh: () => Promise<void>;
    onError: (v: string) => void;
    onNotice: (v: string) => void;
    compact?: boolean;
}) {
    const [comment, setComment] = useState(''), [busy, setBusy] = useState(''), [reporting, setReporting] = useState(false);
    const own = lower(wallet?.address || '') === r.author, ownsRoot = lower(wallet?.address || '') === lower(r.root.owner), ownsRevision = lower(wallet?.address || '') === lower(r.revision.owner);
    const profile = derived?.profiles.get(r.author), authorName = String(profile?.payload.display_name || formatWallet(r.author));
    const currentVote = snapshot?.entities.some(e => e.attributes.kind === 'review-vote' && lower(e.payload.voter) === lower(wallet?.address || '') && lower(e.payload.target_revision_key) === lower(r.revision.key)) || false;
    const days = daysRemaining(r.revision.expires_at_block, snapshot?.block_number ?? r.revision.created_at_block), rootDays = daysRemaining(r.root.expires_at_block, snapshot?.block_number ?? r.root.created_at_block);
    async function vote(value: 'helpful' | 'unhelpful') { if (!wallet || !snapshot) {
        onError('Connect a wallet and wait for reviews to load before voting.');
        return;
    } setBusy(value); try {
        await publishVote(wallet, r.revision, value, snapshot);
        await onRefresh();
    }
    catch (e) {
        onError(e instanceof Error ? e.message : String(e));
    }
    finally {
        setBusy('');
    } }
    async function addComment(e: FormEvent) { e.preventDefault(); if (!wallet || !comment.trim())
        return; setBusy('comment'); try {
        await publishComment(wallet, r.revision, comment);
        setComment('');
        await onRefresh();
    }
    catch (e) {
        onError(e instanceof Error ? e.message : String(e));
    }
    finally {
        setBusy('');
    } }
    async function report(e: FormEvent) { e.preventDefault(); if (!wallet) {
        onError('Connect a wallet before reporting content.');
        return;
    } const details = (e.currentTarget as HTMLFormElement).elements.namedItem('report-details') as HTMLInputElement; const reason = (e.currentTarget as HTMLFormElement).elements.namedItem('report-reason') as HTMLSelectElement; setBusy('report'); try {
        const normalized = lower(wallet.address), detail = details.value.trim(), message = 'Arkiv review report\nreporter:' + normalized + '\nentity_key:' + lower(r.revision.key) + '\nreason:' + reason.value + '\ndetails:' + detail;
        const signature = await wallet.signMessage(message);
        await submitReport({ reporter: normalized, entity_key: lower(r.revision.key), reason: reason.value, details: detail, signature });
        setReporting(false);
        onNotice('Report signed and sent for moderator review.');
    }
    catch (err) {
        onError(err instanceof Error ? err.message : String(err));
    }
    finally {
        setBusy('');
    } }
    async function renew() {
        if(!wallet)return;
        setBusy('renew');
        try {
            await renewReview(wallet,[r.root,...r.revisions]);
            await onRefresh();
        } catch(error) { onError(error instanceof Error?error.message:String(error)); }
        finally { setBusy(''); }
    }
    const game = games.find(g => g.id === r.game_id);
    return <article data-reveal className={'review-card ' + (compact ? 'review-compact' : '')}><div className="review-left"><div className="review-avatar">{authorName[0]?.toUpperCase() || '?'}</div><div><button className="review-author" onClick={() => go({ wallet: r.author, game: undefined })}>{authorName}</button><span className="review-address">{formatWallet(r.author)}</span><span className="review-platform">{r.platform.replaceAll('-', ' ')}</span></div></div><div className="review-content"><div className="review-score"><span aria-label={starText(r.rating_half_stars)}>{'★'.repeat(Math.floor(r.rating_half_stars / 2))}{r.rating_half_stars % 2 ? '½' : ''}</span><b>{starText(r.rating_half_stars)}</b><small className="rep-badge" title="Weighted, decay-aware feedback reputation">Reputation {displayScore(derived?.scores[r.author] ?? 0)}</small><small className="revision-badge">Version {r.revisions.length}</small></div><p className="review-text">{r.text}</p><div className="review-byline"><span>{new Date(r.revision.created_at_timestamp * 1000).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}</span><span>Available for {Math.min(days,rootDays)} more days</span>{game && <button onClick={() => go({ game: game.id })}>{game.title} ↗</button>}</div><div className="review-actions"><button disabled={!wallet || currentVote || busy !== ''} onClick={() => void vote('helpful')}>Helpful <span>{r.helpful}</span></button><button disabled={!wallet || currentVote || busy !== ''} onClick={() => void vote('unhelpful')}>Unhelpful <span>{r.unhelpful}</span></button>{currentVote && <small>You voted on this version</small>}<button className="quiet-action" onClick={() => setReporting(v => !v)}>Report</button><a className="data-link" href={dataExplorerUrl(r.revision.key)} target="_blank" rel="noreferrer">View data ↗</a>{ownsRoot&&ownsRevision&&<button className="quiet-action" disabled={busy!==''} onClick={()=>void renew()}>{busy==='renew'?'Keeping…':'Keep review'}</button>}</div>{reporting && <form className="report-form" onSubmit={report}><span className="select-control"><select name="report-reason"><option value="off_topic">Off topic</option><option value="spam">Spam</option><option value="abuse">Abusive</option><option value="other">Other</option></select></span><input name="report-details" maxLength={300} placeholder="Optional context"/><button disabled={busy === 'report'}>{busy === 'report' ? 'Signing…' : 'Sign report'}</button><small>Reports are reviewed by a moderator.</small></form>}
 <RevisionHistory review={r} derived={derived}/><div className="comments"><p className="comments-title">Comments <span>{r.comments.length}</span></p>{r.comments.map(c => <p className="comment-item" key={c.key}><b>{formatWallet(String(c.payload.author))}</b>{String(c.payload.text)}</p>)}{!compact && <form className="comment-form" onSubmit={addComment}><input value={comment} maxLength={1000} onChange={e => setComment(e.target.value)} placeholder={wallet ? 'Write a comment…' : 'Connect wallet to comment'} disabled={!wallet}/><button disabled={!wallet || !comment.trim() || busy === 'comment'}>{busy === 'comment' ? '…' : '↗'}</button></form>}</div></div></article>;
}
function RevisionHistory({ review, derived }: {
    review: Review;
    derived: Derived | null;
}) {
    const earlier = review.revisions.slice(0, -1);
    if (!earlier.length)
        return null;
    return <details className="revision-history"><summary>Earlier versions ({earlier.length})</summary>{earlier.map(revision => {
            const votes = derived?.canonicalVotes.filter(v => lower(v.payload.target_revision_key) === lower(revision.key)) ?? [];
            return <section key={revision.key}><b>Version {String(revision.payload.revision)} · {starText(Number(revision.payload.rating_half_stars))}</b><p>{String(revision.payload.text)}</p><small>{votes.filter(v => v.payload.value === 'helpful').length} Helpful · {votes.filter(v => v.payload.value === 'unhelpful').length} Unhelpful · Votes remain on this version</small></section>;
        })}</details>;
}
const root = import.meta.hot?.data.root ?? createRoot(document.getElementById('root')!);
if (import.meta.hot) import.meta.hot.data.root = root;
root.render(<React.StrictMode><App/></React.StrictMode>);
