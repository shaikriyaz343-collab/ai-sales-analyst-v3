import { useEffect, useState } from "react";
import { StyleSheet, Text } from "react-native";
import { getReport } from "../../src/api";
import { useData } from "../../src/data";
import { colors } from "../../src/theme";
import { Card, ErrorCard, Header, Loading, Screen } from "../../src/ui";

export default function ReportsScreen() {
  const { state } = useData();
  const [data,setData] = useState<Awaited<ReturnType<typeof getReport>> | null>(null);
  const [busy,setBusy] = useState(true);
  const [error,setError] = useState<string | null>(null);
  useEffect(() => { void load(); }, [state.dataset?.dataset_id,state.sessionId]);
  async function load() {
    if(!state.dataset || !state.sessionId){setBusy(false);return;}
    setBusy(true);setError(null);
    try{setData(await getReport(state.dataset.dataset_id,state.sessionId));}
    catch(err){setError(err instanceof Error ? err.message : "Report could not be loaded.");}
    finally{setBusy(false);}
  }
  if(busy)return <Screen><Loading /></Screen>;
  if(error)return <Screen><ErrorCard message={error} /></Screen>;
  if(!data)return <Screen><ErrorCard message="Choose a workspace with a dataset to continue." /></Screen>;
  return <Screen onRefresh={() => void load()} refreshing={busy}>
    <Header eyebrow="REPORT" title={data.title} subtitle={data.executive_summary} />
    <Card><Text style={styles.section}>Key metrics</Text>{data.metrics.slice(0,8).map(m=><Text key={m.id} style={styles.metric}>{m.label}: <Text style={styles.metricValue}>{m.display_value}</Text></Text>)}</Card>
    <Card><Text style={styles.section}>What changed</Text>{data.what_changed.slice(0,8).map(item=><Text key={item} style={styles.body}>• {item}</Text>)}</Card>
    <Card><Text style={styles.section}>Attention</Text>{data.attention.slice(0,6).map(item=><Text key={item.id} style={styles.body}>• {item.title}: {item.summary}</Text>)}</Card>
    <Card><Text style={styles.section}>Opportunities</Text>{data.opportunities.slice(0,6).map(item=><Text key={item.id} style={styles.body}>• {item.title}: {item.summary}</Text>)}</Card>
    <Card><Text style={styles.section}>Recommended actions</Text>{data.actions.slice(0,8).map(a=><Text key={a.id} style={styles.body}>• {a.title}: {a.action}</Text>)}</Card>
    <Text style={styles.footer}>{data.source_note}</Text>
  </Screen>;
}
const styles=StyleSheet.create({section:{fontSize:16,fontWeight:"800",color:colors.ink},metric:{fontSize:13,lineHeight:21,color:"#59687c"},metricValue:{fontWeight:"800",color:colors.ink},body:{fontSize:13,lineHeight:20,color:"#5f6e82"},footer:{fontSize:10,lineHeight:16,color:"#8a96a8"}});