import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'node:path';
import { realpathSync } from 'node:fs';
const sdkRoot=realpathSync(resolve(__dirname,'../node_modules/@arkiv-network/sdk'));

export default defineConfig({envDir:resolve(__dirname,'..'),plugins:[react()],publicDir:resolve(__dirname,'../../shared/public'),resolve:{dedupe:['viem'],alias:[{find:/^@arkiv-network\/sdk$/,replacement:resolve(sdkRoot,'src/index.ts')},{find:'@arkiv-network/sdk/query',replacement:resolve(sdkRoot,'src/query/index.ts')},{find:'@arkiv-network/sdk/attr',replacement:resolve(sdkRoot,'src/attr/index.ts')},{find:'@arkiv-network/sdk/chains',replacement:resolve(sdkRoot,'src/chains/index.ts')}]},server:{host:'127.0.0.1',port:5174,strictPort:true,fs:{allow:[resolve(__dirname,'../..'),sdkRoot]}},build:{outDir:'dist',emptyOutDir:true}});
