"use client";
import {createContext,useCallback,useContext,useEffect,useMemo,useState} from "react";
import {API_BASE,apiConfigured,apiRequest} from "@/lib/api";
type User={id:string;email:string;full_name:string;email_verified:boolean;phone_number:string|null;phone_verified:boolean};
type AuthContextValue={accessToken:string|null;user:User|null;ready:boolean;apiConfigured:boolean;setSession:(token:string)=>Promise<void>;logout:()=>Promise<void>};
const Context=createContext<AuthContextValue|null>(null);
export function AuthProvider({children}:{children:React.ReactNode}){
  const [accessToken,setAccessToken]=useState<string|null>(null);
  const [user,setUser]=useState<User|null>(null);
  const [ready,setReady]=useState(false);
  const loadUser=useCallback(async(token:string)=>{const me=await apiRequest<User>("/api/v1/auth/me",{},token);setUser(me);},[]);
  const setSession=useCallback(async(token:string)=>{setAccessToken(token);await loadUser(token);},[loadUser]);
  const logout=useCallback(async()=>{const token=accessToken;try{if(token)await apiRequest<void>("/api/v1/auth/logout",{method:"POST"},token);}finally{setAccessToken(null);setUser(null);}},[accessToken]);
  useEffect(()=>{
    let active=true;
    async function restore(){
      if(!apiConfigured){if(active)setReady(true);return;}
      try{const tokens=await apiRequest<{access_token:string}>("/api/v1/auth/refresh",{method:"POST"});if(!active)return;setAccessToken(tokens.access_token);await loadUser(tokens.access_token);}
      catch{if(active){setAccessToken(null);setUser(null);}}
      finally{if(active)setReady(true);}
    }
    void restore();
    return()=>{active=false;};
  },[loadUser]);
  const value=useMemo(()=>({accessToken,user,ready,apiConfigured,setSession,logout}),[accessToken,user,ready,setSession,logout]);
  return <Context.Provider value={value}>{children}</Context.Provider>;
}
export function useAuth(){const value=useContext(Context);if(!value)throw new Error("useAuth must be used within AuthProvider");return value;}
