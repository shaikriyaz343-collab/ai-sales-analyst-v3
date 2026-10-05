import { useEffect, useState } from "react";
import { StyleSheet, Text } from "react-native";
import { getSaved } from "../../src/api";
import { useData } from "../../src/data";
import { colors } from "../../src/theme";
import { Card, ErrorCard, Header, Loading, Screen } from "../../src/ui";

export default function SavedScreen() {
  const { state } = useData();
  const [data,setData] = useState<Awaited<ReturnType<typeof getSaved>> | null>(null);
  const [busy,setBusy] = useState(true);
  const [error,setError] = useState<string | null>(null);
  useEffect(() => { void load(); }, [state.dataset?.dataset_id,state.sessionId]);
  async function load(){
    if(!state.dataset || !state.sessionId){setBusy(false);return;}
    setBusy(true);setError(null);
    try{setData(await getSaved(state.dataset.dataset_id,state.sessionId));}
    catch(err){setError(err instanceof Error ? err.message : "Saved intelligence could not be loaded.");}
    finally{setBusy(false);}
  }
  if(busy)return <Screen><Loading /></Screen>;
  if(error)return <Screen><ErrorCard message={error} /></Screen>;
  if(!data)return <Screen><ErrorCard message="Choose a workspace with a dataset to continue." /></Screen>;
  return <Screen onRefresh={() => void load()} refreshing={busy}>
    <Header eyebrow="SAVED INTELLIGENCE" title="Keep the answers worth revisiting" subtitle="The same saved intelligence is available across web and mobile." />
    {data.items.map(item=><Card key={item.id}><Text style={styles.title}>{item.title || item.name}</Text><Text style={styles.body}>{item.summary}</Text><Text style={styles.meta}>{item.source_workspace} · {item.created_at}</Text></Card>)}
    {data.items.length===0&&<Card><Text style={styles.title}>Nothing saved yet</Text><Text style={styles.body}>Save useful intelligence from the web app and it will appear here.</Text></Card>}
  </Screen>;
}
const styles=StyleSheet.create({title:{fontSize:16,fontWeight:"800",color:colors.ink},body:{fontSize:13,lineHeight:20,color:"#5f6e82"},meta:{fontSize:10,color:"#8a96a8"}});