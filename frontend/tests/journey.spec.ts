import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('suspicious communication to editable complaint export',async({page})=>{
 await page.goto('/');
 await page.getByRole('link',{name:'Check a communication',exact:true}).first().click();
 await page.getByRole('button',{name:'A suspicious refund call'}).click();
 await page.getByRole('button',{name:'Check for warning signs'}).click();
 await expect(page.getByRole('heading',{name:'High concern'})).toBeVisible();
 await expect(page.getByRole('heading',{name:'A request for private credentials'})).toBeVisible();
 await expect(page.getByText('Voice authenticity: unavailable', {exact:true})).toBeVisible();
 await page.screenshot({path:'../artifacts/analysis-desktop.png',fullPage:true});
 await page.getByRole('link',{name:'Prepare a complaint'}).click();
 await page.getByRole('button',{name:'Use my checked conversation'}).click();
 await page.getByLabel('What outcome are you requesting?').fill('Please investigate this suspected impersonation.');
 await page.getByRole('button',{name:'Prepare my draft'}).click();
 await expect(page.getByLabel('Edit complaint draft')).toContainText('suspected impersonation');
 await page.getByLabel('Edit complaint draft').fill('Reviewed complaint: I received a suspicious refund call. Please investigate.');
 const download=page.waitForEvent('download');
 await page.getByRole('button',{name:'Download .txt'}).click();
 expect((await download).suggestedFilename()).toBe('securesense-complaint-draft.txt');
 await page.screenshot({path:'../artifacts/complaint-desktop.png',fullPage:true});
});

test('legitimate message does not produce credential warning',async({page})=>{
 await page.goto('/#/check');
 await page.getByRole('button',{name:'A legitimate refund update'}).click();
 await page.getByRole('button',{name:'Check for warning signs'}).click();
 await expect(page.getByRole('heading',{name:'Few warning signs'})).toBeVisible();
 await expect(page.getByText('No matching warning patterns were found.',{exact:false})).toBeVisible();
 await expect(page.getByRole('heading',{name:'A request for private credentials'})).toHaveCount(0);
});

test('rights and educational scenario are functional',async({page})=>{
 await page.goto('/#/rights');
 await page.getByRole('tab',{name:'redressal'}).click();
 await expect(page.getByRole('heading',{name:'A way to put things right.'})).toBeVisible();
 await expect(page.getByRole('link',{name:'Visit official portal'})).toHaveCount(3);
 await page.getByRole('button',{name:'End the call and contact the business through its official app.'}).click();
 await expect(page.getByRole('status')).toContainText('independent way to verify');
 await page.screenshot({path:'../artifacts/rights-desktop.png',fullPage:true});
});

test('upload rejects unsupported formats',async({page})=>{
 await page.goto('/#/check');
 await page.getByRole('tab',{name:'Add a recording'}).click();
 await page.getByLabel('Choose audio recording').setInputFiles({name:'not-audio.exe',mimeType:'application/octet-stream',buffer:Buffer.from('bad')});
 await expect(page.getByRole('alert')).toContainText('Use WAV, MP3, FLAC or OGG');
 await expect(page.getByRole('button',{name:'Check for warning signs'})).toBeDisabled();
});

test('API failure is visible and retry remains available',async({page})=>{
 await page.route('**/api/v1/analyses/text',r=>r.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Temporary service failure. Please retry.'})}));
 await page.goto('/#/check');
 await page.getByRole('button',{name:'A suspicious refund call'}).click();
 await page.getByRole('button',{name:'Check for warning signs'}).click();
 await expect(page.getByRole('alert')).toContainText('Temporary service failure');
 await expect(page.getByRole('button',{name:'Check for warning signs'})).toBeEnabled();
});

test('history reflects genuine storage availability',async({page,request})=>{
 const caps=await (await request.get('/api/v1/capabilities')).json();
 await page.goto('/#/check');
 await page.getByRole('button',{name:'A suspicious refund call'}).click();
 await page.getByRole('button',{name:'Check for warning signs'}).click();
 await expect(page.getByRole('heading',{name:'High concern'})).toBeVisible();
 await page.getByRole('button',{name:'Save redacted assessment'}).click();
 if(caps.history){
  await expect(page.getByRole('button',{name:'Saved to your activity'})).toBeDisabled();
  await page.getByRole('link',{name:'Your activity',exact:true}).click();
  await expect(page.getByRole('button',{name:/High concern/})).toBeVisible();
  await page.getByRole('button',{name:'Delete assessment'}).click();
  await page.getByRole('button',{name:'Delete',exact:true}).click();
  await expect(page.getByRole('heading',{name:'A clean slate.'})).toBeVisible();
 }else{
  await expect(page.getByRole('status')).toContainText('unavailable');
 }
});

for(const width of [1440,768,390,360]){
 test(`layout and accessibility at ${width}px`,async({page})=>{
  await page.setViewportSize({width,height:1000});
  for(const route of ['/','/#/check','/#/rights','/#/complaint','/#/activity','/#/privacy']){
   await page.goto(route);await page.locator('h1').waitFor();await page.evaluate(()=>document.fonts.ready);
   await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
   const results=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
   expect(results.violations.map(v=>({id:v.id,description:v.description,nodes:v.nodes.map(n=>n.target)}))).toEqual([]);
   if(route==='/'||route==='/#/check')await page.screenshot({path:`../artifacts/${route==='/'?'home':'check'}-${width}.png`,fullPage:true});
  }
 });
}

test('keyboard and mobile navigation',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/');
 await page.keyboard.press('Tab');await expect(page.getByRole('link',{name:'Skip to content'})).toBeFocused();
 await page.getByRole('button',{name:'Menu',exact:true}).click();
 await page.getByRole('link',{name:'Your rights',exact:true}).click();
 await expect(page.getByRole('heading',{name:'These rights belong to you.'})).toBeVisible();
});
