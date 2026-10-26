import type { Game, Snapshot } from './types';
const base = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/,'');
async function read<T>(path:string):Promise<T>{const r=await fetch(base+path); if(!r.ok) throw new Error(path+' returned '+r.status); return r.json() as Promise<T>;}
export const loadSnapshot = () => read<Snapshot>('/api/snapshot');
export const loadCatalog = () => read<{games:Game[]}>('/api/catalog').then(x=>x.games);
export const loadHiddenKeys = () => read<{hidden_keys:string[]}>('/api/moderation').then(x=>x.hidden_keys.map(k=>k.toLowerCase()));
export const submitReport = async(body:unknown) => {const r=await fetch(base+'/api/reports',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)}); if(!r.ok){const data=await r.json().catch(()=>({})); throw new Error(data.detail||'Report failed ('+r.status+')');} return r.json();};
export async function moderateEntity(key:string,hidden:boolean,reason:string,token:string){const r=await fetch(base+'/api/moderation/'+encodeURIComponent(key),{method:'PUT',headers:{'content-type':'application/json',authorization:'Bearer '+token},body:JSON.stringify({hidden,reason})});if(!r.ok){const data=await r.json().catch(()=>({}));throw new Error(data.detail||'Moderation update failed ('+r.status+')');}return r.json();}
