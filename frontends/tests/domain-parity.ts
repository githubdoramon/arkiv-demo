import assert from 'node:assert/strict';
import domainFixture from '../../shared/domain-fixtures.json';
import reputationFixture from '../../shared/reputation-fixtures.json';
import { calculateReputation, derive } from '../shared/src/domain';
import type { Entity, Snapshot } from '../shared/src/types';

const core = domainFixture as {
  snapshot: Snapshot;
  excluded_expired_entities: Entity[];
  expected: { profile_keys:string[]; root_keys:string[]; revision_keys:string[]; vote_keys:string[]; comment_keys:string[]; invalid_entity_keys:string[]; scores:Record<string,number> };
};
const coreProjection = derive(core.snapshot);
const keys = (entities:Entity[]) => entities.map(entity=>entity.key);
assert.deepEqual(keys([...coreProjection.profiles.values()]), core.expected.profile_keys, 'profile canonicalization matches Python fixture');
assert.deepEqual(keys(coreProjection.canonicalRoots), core.expected.root_keys, 'root duplicates resolve to the same Python canonical root');
assert.deepEqual(keys(coreProjection.canonicalRevisions), core.expected.revision_keys, 'longest fork path and duplicate revisions match Python');
assert.deepEqual(keys(coreProjection.canonicalVotes), core.expected.vote_keys, 'duplicate and orphan votes match Python');
assert.deepEqual(keys(coreProjection.canonicalComments), core.expected.comment_keys, 'UUID comment duplicates and invalid comments match Python');
assert.deepEqual(coreProjection.invalidEntityKeys, core.expected.invalid_entity_keys, 'creator, catalog, platform, flag, rating, and orphan validation matches Python');
assertScores(coreProjection.scores, core.expected.scores, 'core domain fixture');

const withExpired = derive({ ...core.snapshot, entities: [...core.snapshot.entities, ...core.excluded_expired_entities] });
assert.deepEqual(keys(withExpired.canonicalRoots), core.expected.root_keys, 'expired root records are absent from canonical output');
assert.deepEqual(keys(withExpired.canonicalRevisions), core.expected.revision_keys, 'expired records do not satisfy live revision dependencies');

const reputation = reputationFixture as {chain_id:number;evaluation_day:number;entities:Entity[];expected_scores:Record<string,number>};
const revisionMap = new Map(reputation.entities.filter(e=>e.attributes.kind==='review-revision').map(e=>[e.key,e]));
const reputationResult = calculateReputation(reputation.entities.filter(e=>e.attributes.kind==='review-vote'), revisionMap, reputation.evaluation_day, new Set(Object.keys(reputation.expected_scores)));
assertScores(reputationResult, reputation.expected_scores, 'shared same-day reputation fixture');

function assertScores(actual:Record<string,number>,expected:Record<string,number>,label:string){
  assert.deepEqual(Object.keys(actual).sort(),Object.keys(expected).sort(),label+' wallet set');
  for(const wallet of Object.keys(expected)) assert.ok(Math.abs(actual[wallet]-expected[wallet])<1e-12,label+' score for '+wallet+': expected '+expected[wallet]+', received '+actual[wallet]);
}

console.log('Frontend canonicalization and reputation parity fixtures passed.');
