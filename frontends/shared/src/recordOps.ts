import { derive, lower } from './domain';
import { createPublicArkivClient, createRecord, ensureConnectedNetwork, type ConnectedWallet } from './arkiv';
import { runTransaction } from './feedback';
import type { Entity, Game, Review, Snapshot } from './types';
import { ExpirationTime, jsonToPayload } from '@arkiv-network/sdk';

export async function publishReview(wallet:ConnectedWallet,snapshot:Snapshot,game:Game,platform:string,ratingHalfStars:number,text:string,existing?:Review) {
  await ensureConnectedNetwork(wallet);
  const author=lower(wallet.address),state=derive(snapshot);
  const current=existing || state.reviews.find(review=>review.author===author&&review.game_id===game.id&&review.platform===platform);
  const root=current?.root || state.canonicalRoots.find(entity=>lower(entity.payload.author)===author&&entity.payload.game_id===game.id&&entity.payload.platform===platform);
  if(!root) {
    const client=createPublicArkivClient();
    const [identity,version]=await client.predictEntityKeys({owner:wallet.address,count:2});
    const rootId=`review:${snapshot.chain_id}:${author}:${game.id}:${platform}`;
    const versionId=`${identity.key}:revision:1`;
    const common={contentType:'application/json',expires:ExpirationTime.fromDays(180),flags:{readonly:true,permissionlessExtension:true}};
    const result=await runTransaction<{txHash:string;createdEntities:string[]}>('Publish review',()=>wallet.client.executeBatch({creates:[
      {...common,salt:identity.salt,payload:jsonToPayload({schema:'review-root/v1',author,game_id:game.id,platform,logical_id:rootId}),attributes:{app:'arkiv-review-demo',kind:'review-root',author,game_id:game.id,platform,logical_id:rootId}},
      {...common,salt:version.salt,payload:jsonToPayload({schema:'review-revision/v1',root_key:identity.key,revision:1,previous_revision_key:null,rating_half_stars:ratingHalfStars,text:text.trim(),author,logical_id:versionId}),attributes:{app:'arkiv-review-demo',kind:'review-revision',root_key:identity.key,revision:1,logical_id:versionId}},
    ]}));
    if(lower(result.createdEntities?.[0])!==lower(identity.key)) throw new Error('Another record was created by this wallet while the review was pending. Refresh before retrying.');
    return result;
  }
  const previous=current?.revision;
  const revision=previous?Number(previous.payload.revision)+1:1;
  const logical_id=`${root.key}:revision:${revision}`;
  return createRecord(wallet,'review-revision','review-revision/v1',{root_key:root.key,revision,previous_revision_key:previous?.key||null,rating_half_stars:ratingHalfStars,text:text.trim(),author,logical_id},{root_key:root.key,revision,logical_id});
}

export async function publishProfile(wallet:ConnectedWallet,snapshot:Snapshot,name:string,bio?:string) {
  await ensureConnectedNetwork(wallet);
  if(!name.trim()||name.trim().length>48) throw new Error('Choose a display name of 1–48 characters.');
  if(bio!==undefined&&bio.length>280)throw new Error('Keep your bio under 280 characters.');
  const address=lower(wallet.address),logical_id=`profile:${snapshot.chain_id}:${address}`;
  const old=derive(snapshot).profiles.get(address);
  const payload={...(old?.payload||{}),schema:'profile/v1',wallet:address,display_name:name.trim(),bio:bio===undefined?String(old?.payload.bio||''):bio.trim(),logical_id};
  if(old)return runTransaction('Save profile',()=>wallet.client.patchEntity({entityKey:old.key,set:{display_name:name.trim()},payload:jsonToPayload(payload)}));
  return createRecord(wallet,'profile','profile/v1',payload,{wallet:address,logical_id},false);
}

export async function publishVote(wallet:ConnectedWallet,revision:Entity,value:'helpful'|'unhelpful',snapshot:Snapshot) {
  const voter=lower(wallet.address),target=lower(revision.key);
  if(derive(snapshot).canonicalVotes.some(entity=>lower(entity.payload.target_revision_key)===target&&lower(entity.payload.voter)===voter))throw new Error('Your vote on this version is already recorded.');
  const logical_id=`vote:${target}:${voter}`;
  return createRecord(wallet,'review-vote','review-vote/v1',{target_revision_key:target,voter,value,logical_id},{target_revision_key:target,voter,logical_id});
}

export async function publishComment(wallet:ConnectedWallet,revision:Entity,text:string) {
  const author=lower(wallet.address),logical_id='comment:'+crypto.randomUUID();
  return createRecord(wallet,'review-comment','review-comment/v1',{target_revision_key:revision.key,author,text:text.trim(),logical_id},{target_revision_key:revision.key,author,logical_id});
}
