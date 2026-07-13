import { createServerClient } from '@supabase/ssr';
const [,, email, password, role] = process.argv;
const URL_='http://127.0.0.1:54321';
const ANON=process.env.ANON, SVC=process.env.SVC;
// ensure user exists with role
const usersResp = await fetch(`${URL_}/auth/v1/admin/users?per_page=200`,{headers:{apikey:SVC,authorization:`Bearer ${SVC}`}}).then(r=>r.json()).catch(()=>({}));
let u=(usersResp.users||[]).find(x=>(x.email||'').toLowerCase()===email.toLowerCase());
if(!u){ u=await fetch(`${URL_}/auth/v1/admin/users`,{method:'POST',headers:{apikey:SVC,authorization:`Bearer ${SVC}`,'content-type':'application/json'},body:JSON.stringify({email,password,email_confirm:true,app_metadata:role?{role}:undefined})}).then(r=>r.json()); }
else if(role){ await fetch(`${URL_}/auth/v1/admin/users/${u.id}`,{method:'PUT',headers:{apikey:SVC,authorization:`Bearer ${SVC}`,'content-type':'application/json'},body:JSON.stringify({app_metadata:{role}})}); }
// password grant -> tokens
const tok=await fetch(`${URL_}/auth/v1/token?grant_type=password`,{method:'POST',headers:{apikey:ANON,'content-type':'application/json'},body:JSON.stringify({email,password})}).then(r=>r.json());
if(!tok.access_token){ console.error('NO_TOKEN '+JSON.stringify(tok)); process.exit(2); }
// use @supabase/ssr to serialize the session into cookies exactly as the app reads them
const jar=[];
const sb=createServerClient(URL_, ANON, { cookies:{ getAll:()=>[], setAll:(cs)=>cs.forEach(c=>jar.push(c)) } });
await sb.auth.setSession({ access_token: tok.access_token, refresh_token: tok.refresh_token });
console.log('COOKIES '+JSON.stringify(jar.map(c=>({name:c.name,value:c.value}))));
