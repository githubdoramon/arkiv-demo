export type Kind = 'profile' | 'review-root' | 'review-revision' | 'review-vote' | 'review-comment';
export type Entity = {
  key: string; creator: string; owner: string; created_at_block: number; created_at_timestamp: number;
  expires_at_block: number; flags: { readonly: boolean; permissionless_extension: boolean };
  attributes: Record<string, unknown>; payload: Record<string, unknown>;
};
export type Snapshot = { chain_id: number; block_number: number; block_timestamp: number; evaluation_day: number; entities: Entity[] };
export type Game = { id: string; title: string; year: number; genres: string[]; platforms: string[]; summary: string; cover_image?: string; cover_source?: string; hero_image?: string };
export type Review = { root: Entity; revision: Entity; revisions: Entity[]; author: string; game_id: string; platform: string; rating_half_stars: number; text: string; helpful: number; unhelpful: number; comments: Entity[]; expires_at_block: number };
export type Derived = { reviews: Review[]; profiles: Map<string, Entity>; scores: Record<string, number>; canonicalRoots: Entity[]; canonicalRevisions: Entity[]; canonicalVotes: Entity[]; canonicalComments: Entity[]; invalidEntityKeys: string[] };
