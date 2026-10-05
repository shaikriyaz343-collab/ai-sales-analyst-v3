import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { createSession, getContext } from "./api";
import { getDatasetId, getSessionId, getWorkspaceId, setDatasetId, setSessionId, setWorkspaceId } from "./storage";
import type { AuthUser, DatasetSummary } from "./types";
import { useAuth } from "./auth";

type DataState = {
  loading: boolean;
  user: AuthUser | null;
  datasets: Record<string, DatasetSummary>;
  workspaceId: string | null;
  dataset: DatasetSummary | null;
  sessionId: string | null;
  error: string | null;
};

const DataContext=createContext<{
  state: DataState;
  refresh: () => Promise<void>;
  selectWorkspace: (id:string)=>Promise<void>;
} | null>(null);

export function DataProvider({children}:{children:React.ReactNode}) {
  const {state:auth}=useAuth();
  const [state,setState]=useState<DataState>({loading:true,user:null,datasets:{},workspaceId:null,dataset:null,sessionId:null,error:null});

  const refresh=useCallback(async()=>{
    if(!auth.token){setState(s=>({...s,loading:false,user:null})); return;}
    setState(s=>({...s,loading:true,error:null}));
    try {
      const context=await getContext();
      const stored=await getWorkspaceId();
      const selected=context.user.workspaces.find(w=>w.id===stored)?.id ?? context.user.workspace_id ?? context.user.workspaces[0]?.id ?? null;
      const dataset=selected ? context.latest_datasets[selected] ?? null : null;
      let sessionId=await getSessionId();
      const storedDataset=await getDatasetId();
      if (!dataset || storedDataset!==dataset.dataset_id) sessionId=null;
      if (dataset && !sessionId) {
        const session=await createSession(dataset.dataset_id,selected!);
        sessionId=session.session_id;
        await setDatasetId(dataset.dataset_id);
        await setSessionId(sessionId);
        await setWorkspaceId(selected!);
      }
      const user=selected ? {...context.user,workspace_id:selected,workspace_name:context.user.workspaces.find(w=>w.id===selected)?.name ?? context.user.workspace_name} : context.user;
      setState({loading:false,user,datasets:context.latest_datasets,workspaceId:selected,dataset,sessionId,error:null});
    } catch(e) {
      setState(s=>({...s,loading:false,error:e instanceof Error?e.message:"Workspace data could not be loaded."}));
    }
  },[auth.token]);

  useEffect(()=>{void refresh();},[refresh]);

  const selectWorkspace=useCallback(async(id:string)=>{
    if(!auth.token) return;
    setState(s=>({...s,loading:true,error:null}));
    try {
      const context=await getContext();
      const dataset=context.latest_datasets[id] ?? null;
      let sessionId:string|null=null;
      if(dataset){
        const session=await createSession(dataset.dataset_id,id);
        sessionId=session.session_id;
        await setWorkspaceId(id);
        await setDatasetId(dataset.dataset_id);
        await setSessionId(sessionId);
      } else {
        await setWorkspaceId(id);
        await setDatasetId("");
        await setSessionId("");
      }
      const workspace=context.user.workspaces.find(w=>w.id===id);
      const user={...context.user,workspace_id:id,workspace_name:workspace?.name ?? context.user.workspace_name};
      setState({loading:false,user,datasets:context.latest_datasets,workspaceId:id,dataset,sessionId,error:null});
    } catch(e) {
      setState(s=>({...s,loading:false,error:e instanceof Error?e.message:"Workspace could not be selected."}));
    }
  },[auth.token]);

  const value=useMemo(()=>({state,refresh,selectWorkspace}),[state,refresh,selectWorkspace]);
  return <DataContext.Provider value={value}>{children}</DataContext.Provider>;
}
export function useData(){const value=useContext(DataContext);if(!value)throw new Error("useData must be used inside DataProvider");return value;}
