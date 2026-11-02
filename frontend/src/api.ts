export type Evidence = {id:string;title:string;weight:number;excerpt:string;start:number;end:number;explanation:string;action:string};
export type Analysis = {id:string;created_at:string;transcript:string;provenance:string;context:string;policy_version:string;level:'high'|'moderate'|'low'|'insufficient';score:number|null;summary:string;evidence:Evidence[];actions:string[];rights:string[];limitations:string[];saved:boolean;audio?:{duration:number;sample_rate:number;channels:number}};
export type Right = {id:string;title:string;short:string;body:string;example:string;source:string;reviewed:string};
export type Channel = {id:string;title:string;label:string;description:string;url:string;phone:string|null;source:string};
export type Capabilities = {history:boolean;transcription:boolean;text_analysis:boolean;retention_days:number};
export type Job = {id:string;stage:string;result?:Analysis;error?:string};

export async function api<T>(path:string, options:RequestInit = {}):Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(()=>controller.abort(),35000);
  try {
    const response = await fetch('/api/v1'+path,{...options,credentials:'same-origin',signal:options.signal || controller.signal,
      headers:{'X-SecureSense':'1',...(options.body instanceof FormData ? {} : {'Content-Type':'application/json'}),...options.headers}});
    const data = await response.json().catch(()=>({detail:'The service returned an unreadable response.'}));
    if(!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Check your input and try again.');
    return data;
  } catch(error) {
    if(error instanceof DOMException && error.name==='AbortError') throw new Error('The request timed out. Please retry.');
    if(error instanceof TypeError) throw new Error('SecureSense could not reach its local API. Check that the backend is running.');
    throw error;
  } finally {clearTimeout(timer);}
}
export function download(name:string,text:string) {
  const link=document.createElement('a'); const url=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));
  link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
export const labels = {high:'High concern',moderate:'Needs a closer look',low:'Few warning signs',insufficient:'Insufficient evidence'};
export const scenarios = {
  refund:"I'm calling from Amazon about your refund. Pay a processing fee to release your refund. Tell me your OTP immediately. Don't tell your family.",
  safe:"Your refund has been processed to your original payment method. Never share your OTP or password. Check the status in the official shopping app.",
  support:"I am from customer support. Install AnyDesk and share your screen. Transfer money right now or your account will be blocked."
};
