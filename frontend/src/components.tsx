import {useEffect,useState} from 'react';
import {ArrowUpRight,ArrowRight,ShieldCheck,LoaderCircle,LockKeyhole,ExternalLink} from 'lucide-react';
import type {ReactNode} from 'react';

export function Button({children,onClick,secondary=false,disabled=false,type='button',className=''}:{children:ReactNode;onClick?:()=>void;secondary?:boolean;disabled?:boolean;type?:'button'|'submit';className?:string}) {
 return <button type={type} onClick={onClick} disabled={disabled} className={`button ${secondary?'secondary':''} ${className}`}>{children}</button>;
}
export function ArrowLink({to,children}:{to:string;children:ReactNode}) {return <a className="text-link" href={'#'+to}>{children}<ArrowUpRight size={17}/></a>}
export function SectionLabel({children}:{children:ReactNode}) {return <div className="eyebrow"><span/>{children}</div>}
export function Notice({children,error=false}:{children:ReactNode;error?:boolean}) {return <div className={`notice ${error?'error':''}`} role={error?'alert':'status'}>{children}</div>}
export function Spinner({text}:{text:string}) {return <div className="processing" role="status"><LoaderCircle className="spin" size={24}/><span>{text}</span></div>}
export function External({url,children}:{url:string;children:ReactNode}) {return <a href={url} target="_blank" rel="noopener noreferrer" className="text-link">{children}<ExternalLink size={14}/><span className="sr-only"> (opens in a new tab)</span></a>}
export function PrivacyNote() {return <p className="privacy-note"><LockKeyhole size={14}/> Processed on this computer. Nothing saved unless you choose.</p>}
export function Header({route}:{route:string}) {
 const [open,setOpen]=useState(false);
 useEffect(()=>setOpen(false),[route]);
 return <header className="header"><div className="header-inner"><a className="brand" href="#/" aria-label="SecureSense home"><span className="brand-symbol"><ShieldCheck size={24}/></span>Secure<span>Sense</span><sup>2.0</sup></a><button className="menu-toggle" aria-expanded={open} onClick={()=>setOpen(!open)}>{open?'Close':'Menu'}</button><nav className={open?'open':''} aria-label="Main navigation">{[['/check','Check a communication'],['/rights','Your rights'],['/activity','Your activity']].map(([href,label])=><a key={href} href={'#'+href} aria-current={route.startsWith(href)?'page':undefined}>{label}</a>)}<a href="#/complaint" className="nav-action">Get complaint help<ArrowUpRight size={15}/></a></nav></div></header>
}
export function Footer(){return <footer className="footer"><div><a className="brand" href="#/"><ShieldCheck size={20}/>SecureSense</a><p>Know your rights. Verify the voice. Prevent the fraud.</p></div><div><a href="#/privacy">Privacy & limitations</a><span>Built for informed decisions. Made for India.</span></div></footer>}
export function Steps({active=0}:{active?:number}){return <div className="steps" aria-label="Analysis workflow">{['Add a communication','Understand the signs','Choose your next step'].map((s,i)=><div className={i<=active?'active':''} key={s}><span>{String(i+1).padStart(2,'0')}</span>{s}{i<2&&<ArrowRight size={15}/>}</div>)}</div>}
export function Waveform({file}:{file:File}) {
 const [url,setUrl]=useState(''); const [peaks,setPeaks]=useState<number[]>([]); const [error,setError]=useState('');
 useEffect(()=>{let alive=true;const objectUrl=URL.createObjectURL(file);setUrl(objectUrl);setError('');setPeaks([]);
 const context=new AudioContext();
 file.arrayBuffer().then(b=>context.decodeAudioData(b)).then(buffer=>{if(!alive)return; const samples=buffer.getChannelData(0);const stride=Math.max(1,Math.floor(samples.length/90));setPeaks(Array.from({length:90},(_,i)=>{let peak=0;for(let j=i*stride;j<Math.min((i+1)*stride,samples.length);j+=Math.max(1,Math.floor(stride/100)))peak=Math.max(peak,Math.abs(samples[j]));return peak;}));}).catch(()=>{if(alive)setError('Browser preview is unavailable for this format. The server will validate the recording.');}).finally(()=>context.close());
 return()=>{alive=false;URL.revokeObjectURL(objectUrl);};},[file]);
 return <div className="audio-preview">{peaks.length>0&&<svg viewBox="0 0 540 70" role="img" aria-label="Waveform of your recording">{peaks.map((v,i)=><line key={i} x1={i*6+2} x2={i*6+2} y1={35-Math.max(2,v*32)} y2={35+Math.max(2,v*32)} stroke="currentColor" strokeWidth="3" strokeLinecap="round"/>)}</svg>}<audio aria-label="Play your recording" controls src={url}/>{error&&<p className="small">{error}</p>}</div>
}
