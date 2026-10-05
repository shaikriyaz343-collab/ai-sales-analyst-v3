import { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { getActions } from "../../src/api";
import { useData } from "../../src/data";
import { colors } from "../../src/theme";
import { Badge, Card, ErrorCard, Header, Loading, Screen } from "../../src/ui";

export default function DecisionsScreen() {
  const { state } = useData();
  const [data, setData] = useState<Awaited<ReturnType<typeof getActions>> | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { void load(); }, [state.dataset?.dataset_id, state.sessionId]);
  async function load() {
    if (!state.dataset || !state.sessionId) { setBusy(false); return; }
    setBusy(true); setError(null);
    try { setData(await getActions(state.dataset.dataset_id, state.sessionId)); }
    catch (err) { setError(err instanceof Error ? err.message : "Decisions could not be loaded."); }
    finally { setBusy(false); }
  }
  if (busy && !data) return <Screen><Loading /></Screen>;
  if (error) return <Screen><ErrorCard message={error} /></Screen>;
  if (!data) return <Screen><Header title="Decisions" /><ErrorCard message="Choose a workspace with a dataset to continue." /></Screen>;
  return <Screen onRefresh={() => void load()} refreshing={busy}>
    <Header eyebrow={data.business_model_label || "DECISION COCKPIT"} title={data.headline} subtitle={data.summary} />
    {data.actions.slice(0, 10).map(item => <Card key={item.id}>
      <View style={styles.top}><Badge tone={item.priority === "high" ? "danger" : item.priority === "medium" ? "warning" : "neutral"}>{item.priority}</Badge><Text style={styles.value}>{item.display_value}</Text></View>
      <Text style={styles.title}>{item.title}</Text>
      <Text style={styles.body}>{item.action}</Text>
      <Text style={styles.owner}>Owner: {item.owner}</Text>
      <Text style={styles.reco}>{item.expected_outcome}</Text>
      <Text style={styles.evidence}>{item.evidence.calculation}</Text>
    </Card>)}
    {data.actions.length === 0 && <Card><Text style={styles.title}>No ranked decisions</Text><Text style={styles.body}>No validated decision signals are available.</Text></Card>}
  </Screen>;
}

const styles=StyleSheet.create({
  top:{flexDirection:"row",justifyContent:"space-between",alignItems:"center"},
  value:{fontSize:18,fontWeight:"900",color:colors.ink},
  title:{fontSize:17,fontWeight:"800",color:colors.ink},
  body:{fontSize:13,lineHeight:20,color:"#5f6e82"},
  owner:{fontSize:11,color:"#7e8b9d"},
  reco:{fontSize:12,lineHeight:19,color:colors.accent},
  evidence:{fontSize:11,lineHeight:18,color:"#8a96a8"}
});