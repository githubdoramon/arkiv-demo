import {reviewAppUrl,networkConfig} from './config';
import { useEffect, useState } from 'react';
import { createPublicArkivClient } from './arkiv';
import { dataExplorerUrl } from './feedback';

const json=(value:unknown)=>JSON.stringify(value,(_key,item)=>typeof item==='bigint'?item.toString():item,2);

export function DataExplorer({entityKey,transactionHash}:{entityKey?:string|null;transactionHash?:string|null}) {
  const [data,setData]=useState<Record<string,unknown>|null>(null);
  const [error,setError]=useState('');
  useEffect(()=>{
    let active=true;
    async function load(){
      try{
        const client=createPublicArkivClient();
        if(transactionHash){
          const [transaction,receipt]=await Promise.all([client.getTransaction({hash:transactionHash}),client.getTransactionReceipt({hash:transactionHash})]);
          if(active)setData({transaction,receipt});
        }else if(entityKey){
          const entity=await client.getEntity(entityKey);
          let payload:unknown;
          try{payload=entity.toJson();}catch{payload=entity.toText();}
          if(active)setData({key:entity.key,creator:entity.creator,owner:entity.owner,created_at_block:entity.createdAt,updated_at_block:entity.updatedAt,expires_at_block:entity.expiresAt,flags:entity.creationFlags,attributes:entity.attributes,payload});
        }
      }catch{if(active)setError('This record could not be loaded. It may have expired or belong to another network.');}
    }
    void load();return()=>{active=false;};
  },[entityKey,transactionHash]);
  const payload=data?.payload as Record<string,unknown>|undefined;
  const references=payload?Object.entries(payload).filter(([key,value])=>key.endsWith('_key')&&typeof value==='string'&&/^0x[0-9a-f]{64}$/i.test(value)):[];
  return <main className="data-explorer">
    <header><a href={reviewAppUrl}>← Back to Sidequest</a><span>Data explorer</span></header>
    <h1>{transactionHash?'Transaction':'Record data'}</h1>
    <p className="explorer-network">{networkConfig.name} · Chain {networkConfig.id}</p>
    <code className="explorer-key">{transactionHash||entityKey}</code>
    {error?<p role="alert">{error}</p>:!data?<p>Loading data…</p>:<>
      {references.length>0&&<nav className="explorer-references">{references.map(([key,value])=><a key={key} href={dataExplorerUrl(String(value))}>{key.replaceAll('_',' ')}</a>)}</nav>}
      <pre>{json(data)}</pre>
    </>}
  </main>;
}
