import type { Derived, Entity, Game, Snapshot } from './types';
import gamesJson from '../../../shared/games.json';

export const APP = 'arkiv-review-demo';
export const CURATED_GAMES = gamesJson as Game[];
export const lower = (s: unknown) => String(s ?? '').toLowerCase();
export const payload = (e: Entity) => e.payload && typeof e.payload === 'object' ? e.payload : {};
export const attr = (e: Entity, key: string) => e.attributes?.[key];
const sortCreated = (a: Entity, b: Entity) => a.created_at_block - b.created_at_block || lower(a.key).localeCompare(lower(b.key));
const validText = (value: unknown) => typeof value === 'string' && value.trim().length > 0;
const walletKey = (value: unknown): string | null => typeof value === 'string' && /^0x[0-9a-fA-F]{40}$/.test(value) ? value.toLowerCase() : null;
const entityKey = (value: unknown): string | null => typeof value === 'string' && /^0x[0-9a-fA-F]{64}$/.test(value) ? value.toLowerCase() : null;
const identity = (e: Entity, who: unknown) => !!who && walletKey(e.creator) !== null && walletKey(e.creator) === walletKey(who);
const hasFlags = (e: Entity, readonly: boolean) => e.flags?.readonly === readonly && e.flags?.permissionless_extension === true;
const validEntity = (e: Entity, kind: string, schema: string) => attr(e, 'app') === APP && attr(e, 'kind') === kind && payload(e).schema === schema;

function uniqueCanonical(entities: Entity[], id: (e: Entity) => string) {
  const groups = new Map<string, Entity[]>();
  for (const e of entities) {
    const key = id(e);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(e);
  }
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([, group]) => [...group].sort(sortCreated)[0]);
}

function comparePaths(a: Entity[], b: Entity[]) {
  if (a.length !== b.length) return b.length - a.length;
  for (let i = 0; i < a.length; i++) {
    const diff = sortCreated(a[i], b[i]);
    if (diff) return diff;
  }
  return 0;
}

function resolveChains(candidates: Entity[]) {
  const byPreviousAndNumber = new Map<string, Entity[]>();
  for (const revision of candidates) {
    const p = payload(revision);
    const parent = p.previous_revision_key == null ? '' : String(p.previous_revision_key);
    const id = parent + '|' + String(p.revision);
    if (!byPreviousAndNumber.has(id)) byPreviousAndNumber.set(id, []);
    byPreviousAndNumber.get(id)!.push(revision);
  }
  for (const list of byPreviousAndNumber.values()) list.sort(sortCreated);

  const pathsFrom = (revision: Entity): Entity[][] => {
    const nextId = lower(revision.key) + '|' + String(Number(payload(revision).revision) + 1);
    const children = byPreviousAndNumber.get(nextId) ?? [];
    if (!children.length) return [[revision]];
    return children.flatMap(child => pathsFrom(child).map(path => [revision, ...path]));
  };
  const starts = byPreviousAndNumber.get('|1') ?? [];
  const paths = starts.flatMap(first => pathsFrom(first));
  return paths.sort(comparePaths)[0] ?? [];
}

function normalizedEntity(e: Entity, data: Record<string, unknown>): Entity {
  return { ...e, key: entityKey(e.key)!, creator: walletKey(e.creator)!, owner: walletKey(e.owner) ?? lower(e.owner), payload: data };
}

function uuidIsCanonical(value: unknown) {
  if (typeof value !== 'string' || !value.startsWith('comment:')) return false;
  const id = value.slice('comment:'.length);
  return /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/.test(id);
}

export function derive(snapshot: Snapshot, catalog: Game[] = CURATED_GAMES): Derived {
  const active = snapshot.entities.filter(e => e.expires_at_block > snapshot.block_number);
  const gameById = new Map(catalog.map(game => [game.id, game]));
  const invalid = new Set<string>();
  const reject = (e: Entity) => { if (e.key) invalid.add(lower(e.key)); };
  const profileCandidates: Entity[] = [], rootCandidates: Entity[] = [], revisionCandidates: Entity[] = [];
  const voteCandidates: Entity[] = [], commentCandidates: Entity[] = [];

  for (const e of active) {
    const kind = attr(e, 'kind');
    if (attr(e, 'app') !== APP || !['profile','review-root','review-revision','review-vote','review-comment'].includes(String(kind))) continue;
    if (!entityKey(e.key) || !walletKey(e.creator)) { reject(e); continue; }
    const p = payload(e), a = e.attributes ?? {};
    if (kind === 'profile') {
      const wallet = walletKey(p.wallet), logical = wallet ? 'profile:' + snapshot.chain_id + ':' + wallet : null;
      if (wallet !== walletKey(e.creator) || p.logical_id !== logical || walletKey(a.wallet) !== wallet || a.logical_id !== logical || !validText(p.display_name) || !hasFlags(e, false)) { reject(e); continue; }
      profileCandidates.push(normalizedEntity(e, { ...p, wallet }));
    } else if (kind === 'review-root') {
      const author = walletKey(p.author), gameId = p.game_id, platform = p.platform;
      const game = typeof gameId === 'string' ? gameById.get(gameId) : undefined;
      const logical = author ? 'review:' + snapshot.chain_id + ':' + author + ':' + String(gameId) + ':' + String(platform) : null;
      if (author !== walletKey(e.creator) || !game || typeof platform !== 'string' || !game.platforms.includes(platform) || p.logical_id !== logical || walletKey(a.author) !== author || a.game_id !== gameId || a.platform !== platform || a.logical_id !== logical || !hasFlags(e, true)) { reject(e); continue; }
      rootCandidates.push(normalizedEntity(e, { ...p, author }));
    } else if (kind === 'review-revision') {
      const root = entityKey(p.root_key), author = walletKey(p.author), revision = p.revision, previous = p.previous_revision_key, rating = p.rating_half_stars;
      const normalizedPrevious = previous == null ? null : entityKey(previous);
      if (!root || !author || author !== walletKey(e.creator) || typeof revision !== 'number' || !Number.isInteger(revision) || revision < 1 || (revision === 1 && previous !== null) || (revision > 1 && !normalizedPrevious) || typeof rating !== 'number' || !Number.isInteger(rating) || rating < 2 || rating > 10 || !validText(p.text) || p.logical_id !== root + ':revision:' + revision || entityKey(a.root_key) !== root || a.revision !== revision || a.logical_id !== p.logical_id || !hasFlags(e, true)) { reject(e); continue; }
      revisionCandidates.push(normalizedEntity(e, { ...p, root_key: root, author, previous_revision_key: normalizedPrevious }));
    } else if (kind === 'review-vote') {
      const target = entityKey(p.target_revision_key), voter = walletKey(p.voter);
      const logical = target && voter ? 'vote:' + target + ':' + voter : null;
      if (!target || !voter || voter !== walletKey(e.creator) || !['helpful','unhelpful'].includes(String(p.value)) || p.logical_id !== logical || entityKey(a.target_revision_key) !== target || walletKey(a.voter) !== voter || a.logical_id !== logical || !hasFlags(e, true)) { reject(e); continue; }
      voteCandidates.push(normalizedEntity(e, { ...p, target_revision_key: target, voter }));
    } else {
      const target = entityKey(p.target_revision_key), author = walletKey(p.author), logical = p.logical_id;
      if (!target || !author || author !== walletKey(e.creator) || !uuidIsCanonical(logical) || !validText(p.text) || entityKey(a.target_revision_key) !== target || walletKey(a.author) !== author || a.logical_id !== logical || !hasFlags(e, true)) { reject(e); continue; }
      commentCandidates.push(normalizedEntity(e, { ...p, target_revision_key: target, author }));
    }
  }

  const profiles = uniqueCanonical(profileCandidates, e => String(payload(e).wallet));
  const roots = uniqueCanonical(rootCandidates, e => snapshot.chain_id + '|' + payload(e).author + '|' + payload(e).game_id + '|' + payload(e).platform);
  const rootByKey = new Map(roots.map(root => [lower(root.key), root]));
  const attachedRevisions = revisionCandidates.filter(revision => {
    const root = rootByKey.get(lower(String(payload(revision).root_key)));
    if (!root || lower(payload(revision).author) !== lower(payload(root).author)) { reject(revision); return false; }
    return true;
  });
  const revisionsByRoot = new Map<string, Entity[]>();
  for (const revision of attachedRevisions) {
    const key = lower(String(payload(revision).root_key));
    if (!revisionsByRoot.has(key)) revisionsByRoot.set(key, []);
    revisionsByRoot.get(key)!.push(revision);
  }
  const canonicalRevisions = roots.flatMap(root => resolveChains(revisionsByRoot.get(lower(root.key)) ?? []));
  const canonicalRevisionByKey = new Map(canonicalRevisions.map(revision => [lower(revision.key), revision]));

  const attachedVotes = voteCandidates.filter(vote => {
    if (!canonicalRevisionByKey.has(lower(String(payload(vote).target_revision_key)))) { reject(vote); return false; }
    return true;
  });
  const votes = uniqueCanonical(attachedVotes, e => lower(payload(e).target_revision_key) + '|' + lower(payload(e).voter));
  const attachedComments = commentCandidates.filter(comment => {
    if (!canonicalRevisionByKey.has(lower(String(payload(comment).target_revision_key)))) { reject(comment); return false; }
    return true;
  });
  const comments = uniqueCanonical(attachedComments, e => String(payload(e).logical_id));

  const voteByRevision = new Map<string, Entity[]>(), commentsByRevision = new Map<string, Entity[]>();
  for (const vote of votes) {
    const key = lower(String(payload(vote).target_revision_key));
    if (!voteByRevision.has(key)) voteByRevision.set(key, []);
    voteByRevision.get(key)!.push(vote);
  }
  for (const comment of comments) {
    const key = lower(String(payload(comment).target_revision_key));
    if (!commentsByRevision.has(key)) commentsByRevision.set(key, []);
    commentsByRevision.get(key)!.push(comment);
  }

  const reviews = roots.flatMap(root => {
    const chain = canonicalRevisions.filter(revision => lower(String(payload(revision).root_key)) === lower(root.key));
    if (!chain.length) return [];
    const latest = chain[chain.length - 1], latestPayload = payload(latest);
    const currentVotes = voteByRevision.get(lower(latest.key)) ?? [];
    const currentComments = [...(commentsByRevision.get(lower(latest.key)) ?? [])].sort(sortCreated);
    return [{
      root, revision: latest, revisions: chain, author: lower(payload(root).author),
      game_id: String(payload(root).game_id), platform: String(payload(root).platform),
      rating_half_stars: Number(latestPayload.rating_half_stars), text: String(latestPayload.text),
      helpful: currentVotes.filter(v => payload(v).value === 'helpful').length,
      unhelpful: currentVotes.filter(v => payload(v).value === 'unhelpful').length,
      comments: currentComments, expires_at_block: Math.min(root.expires_at_block, ...chain.map(r => r.expires_at_block)),
    }];
  });

  const knownWallets = new Set<string>();
  profiles.forEach(e => knownWallets.add(lower(payload(e).wallet)));
  roots.forEach(e => knownWallets.add(lower(payload(e).author)));
  votes.forEach(e => knownWallets.add(lower(payload(e).voter)));
  comments.forEach(e => knownWallets.add(lower(payload(e).author)));
  const scores = calculateReputation(votes, canonicalRevisionByKey, snapshot.evaluation_day, knownWallets);
  return { reviews, profiles: new Map(profiles.map(e => [lower(payload(e).wallet), e])), scores, canonicalRoots: roots, canonicalRevisions, canonicalVotes: votes, canonicalComments: comments, invalidEntityKeys: [...invalid].filter(Boolean).sort() };
}

export function calculateReputation(votes: Entity[], revisions: Map<string,Entity>, evaluationDay: number, knownWallets = new Set<string>()): Record<string,number> {
  const events = votes.map(v => ({ vote: v, day: Math.floor(v.created_at_timestamp / 86400) }))
    .filter(x => x.day <= evaluationDay)
    .sort((a,b) => a.day-b.day || a.vote.created_at_block-b.vote.created_at_block || lower(a.vote.key).localeCompare(lower(b.vote.key)));
  const evidence = new Map<string, Array<{day:number; amount:number}>>();
  const interactions: Array<{day:number; voter:string; author:string}> = [];
  const users = new Set([...knownWallets].map(lower));
  for (const event of events) { users.add(lower(payload(event.vote).voter)); }
  for (const revision of revisions.values()) users.add(lower(payload(revision).author));

  const scoresAt = (day:number) => {
    const totals:Record<string,number> = {};
    for (const user of users) totals[user] = 0;
    for (const [author, items] of evidence) {
      totals[author] = (totals[author] ?? 0) + items.reduce((sum,item)=>sum+item.amount*Math.pow(2,-(day-item.day)/90),0);
    }
    for (const user of users) totals[user] = Math.max(0,Math.min(1000,totals[user] ?? 0));
    return totals;
  };

  let cursor=0;
  while(cursor<events.length){
    const day=events[cursor].day, frozen=scoresAt(day);
    while(cursor<events.length&&events[cursor].day===day){
      const vote=events[cursor++].vote, revision=revisions.get(lower(payload(vote).target_revision_key));
      if(!revision) continue;
      const author=lower(payload(revision).author), voter=lower(payload(vote).voter);
      if(!author||!voter||author===voter||!['helpful','unhelpful'].includes(String(payload(vote).value))) continue;
      const recent=interactions.filter(x=>x.voter===voter&&x.author===author&&day-x.day>=0&&day-x.day<30).length;
      const repeatCount=recent+1;
      const repeatFactor=repeatCount<=5?1/repeatCount:0;
      const voterScore=Math.max(0,Math.min(1000,frozen[voter]??0));
      const weight=.001+.999*voterScore/(voterScore+20);
      const sign=payload(vote).value==='helpful'?1:-1;
      if(!evidence.has(author)) evidence.set(author,[]);
      evidence.get(author)!.push({day,amount:sign*weight*repeatFactor});
      interactions.push({day,voter,author});
    }
  }
  return scoresAt(evaluationDay);
}

export const walletScore = (d:Derived,wallet:string) => d.scores[lower(wallet)] ?? 0;
export const formatWallet = (wallet:string) => wallet ? wallet.slice(0,6)+'…'+wallet.slice(-4) : 'Unknown wallet';
export const starText = (halfStars:number) => (halfStars/2).toFixed(1)+' / 5';
export const displayScore = (score:number) => score === 0 ? '0' : Math.abs(score) < .01 ? score.toPrecision(3).replace(/(?:\.0+|(\.\d*?)0+)$/, '$1') : score.toFixed(3).replace(/\.?0+$/, '');
export const daysRemaining = (expiryBlock:number, block:number) => Math.max(0,Math.ceil((expiryBlock-block)*2/86400));
