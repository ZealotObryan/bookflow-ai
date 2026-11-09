const rawBase=process.env.NEXT_PUBLIC_API_BASE_URL;
export const API_BASE=rawBase?.replace(/\/+$/,"")||"";
export const apiConfigured=Boolean(API_BASE);
export async function apiRequest<T>(path:string,options:RequestInit={},accessToken?:string):Promise<T>{
  if(!API_BASE)throw new Error("The BookFlow API has not been connected yet. This workspace is currently in preview mode.");
  const headers=new Headers(options.headers);
  if(options.body&&!headers.has("Content-Type"))headers.set("Content-Type","application/json");
  if(accessToken)headers.set("Authorization","Bearer "+accessToken);
  const response=await fetch(API_BASE+path,{...options,headers,credentials:"include",cache:"no-store"});
  if(response.status===204)return undefined as T;
  const body=await response.json().catch(()=>({detail:"The server returned an unreadable response."}));
  if(!response.ok)throw new Error(body.detail||"The request could not be completed.");
  return body as T;
}
