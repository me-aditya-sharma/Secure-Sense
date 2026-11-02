import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',fullyParallel:false,workers:1,timeout:45000,reporter:[['list'],['html',{open:'never'}]],use:{baseURL:'http://127.0.0.1:8001',channel:'msedge',headless:true,trace:'retain-on-failure',screenshot:'only-on-failure',viewport:{width:1440,height:1000}},outputDir:'test-results'});
