import { useState } from 'react';
import { Icon, platformName, type Game, type Review } from '@sidequest/shared';

export function LibraryFilters({search,onSearch,genre,onGenre,platform,onPlatform,games}:{search:string;onSearch:(v:string)=>void;genre:string;onGenre:(v:string)=>void;platform:string;onPlatform:(v:string)=>void;games:Game[]}) {
  return <div className="library-filters">
    <label className="search-box"><Icon name="search"/><input type="search" value={search} onChange={e=>onSearch(e.target.value)} placeholder="Find your next game" aria-label="Search games"/></label>
    <label><span className="sr-only">Filter by genre</span><span className="select-control"><select value={genre} onChange={e=>onGenre(e.target.value)}><option value="all">All genres</option>{[...new Set(games.flatMap(g=>g.genres))].sort().map(g=><option key={g}>{g}</option>)}</select></span></label>
    <label><span className="sr-only">Filter by platform</span><span className="select-control"><select value={platform} onChange={e=>onPlatform(e.target.value)}><option value="all">All platforms</option>{[...new Set(games.flatMap(g=>g.platforms))].sort().map(p=><option key={p} value={p}>{platformName(p)}</option>)}</select></span></label>
  </div>;
}

export function GameLibrary({games,visible,reviews,loading,filtered,onReset,onGame}:{games:Game[];visible:Game[];reviews:Review[];loading:boolean;filtered:boolean;onReset:()=>void;onGame:(id:string)=>void}) {
  const [selected,setSelected]=useState('hades');
  const spotlight=['baldurs-gate-3','hades','dave-the-diver','dead-cells'].map(id=>games.find(g=>g.id===id)).filter((g):g is Game=>!!g);
  const game=games.find(g=>g.id===selected)||spotlight[0];
  return <>
    {!filtered&&game&&<section className="library-stage" aria-label="Featured games">
      <div className="stage-backdrop" aria-hidden="true" key={game.id}><img src={'/games/'+game.id+(['hades','baldurs-gate-3','elden-ring'].includes(game.id)?'-hero':'')+'.jpg'} alt=""/></div>
      <div className="poster-gallery">{spotlight.map((item,i)=><button key={item.id} className={'gallery-poster poster-'+i+(item.id===game.id?' is-selected':'')} aria-pressed={item.id===game.id} aria-label={'Select '+item.title} onClick={()=>setSelected(item.id)}><img src={'/games/'+item.id+'.jpg'} width="600" height="900" alt={item.title+' cover art'} fetchPriority={item.id==='hades'?'high':undefined}/><span className="poster-caption">{item.title}<Icon name="arrow"/></span></button>)}</div>
      <div className="selection-strip"><h1>{game.title}</h1><p>{game.summary}</p><div className="selection-tags"><div>{game.platforms.map(p=><span key={p}>{platformName(p)}</span>)}</div><small>{game.genres.join(' / ')}</small></div><button className="primary-btn" onClick={()=>onGame(game.id)}>Read reviews <Icon name="arrow"/></button></div>
    </section>}
    <section className="catalog-section" aria-labelledby="catalog-heading"><div className="section-heading"><h2 id="catalog-heading">{filtered?'Search results':'The collection'} <span>{visible.length}</span></h2><p>{filtered?'Find a game. Find a different point of view.':'Good games. Honest opinions. Wherever you play.'}</p></div>
      {loading&&<p className="loading-state" role="status">Gathering the latest player reviews…</p>}
      {visible.length?<div className="game-grid">{visible.map(game=>{
        const notes=reviews.filter(r=>r.game_id===game.id), average=notes.length?notes.reduce((s,r)=>s+r.rating_half_stars,0)/notes.length/2:null;
        return <button className="game-card" key={game.id} onClick={()=>onGame(game.id)}><div className="card-cover"><img src={'/games/'+game.id+'.jpg'} width="600" height="900" loading="lazy" alt={game.title+' cover art'}/><span className="cover-open"><Icon name="arrow"/></span></div><div className="card-meta"><h3>{game.title}</h3><span>{game.year}</span></div><div className="card-foot"><span>{notes.length?notes.length+' '+(notes.length===1?'review':'reviews'):'Be the first to review'}</span>{average!==null&&<b aria-label={average.toFixed(1)+' out of 5 stars'}>★ {average.toFixed(1)}</b>}</div></button>;
      })}</div>:<div className="empty-state"><h3>No games found.</h3><p>Try a different title, genre or platform.</p><button onClick={onReset}>Reset filters</button></div>}
    </section>
    <footer className="site-footer"><span className="footer-brand">Sidequest</span><p>Every game has a story.<br/>Tell yours.</p><a href="#top">Back to top <Icon name="arrow"/></a></footer>
  </>;
}
