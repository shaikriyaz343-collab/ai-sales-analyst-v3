import { useEffect, useState } from "react";
import { StyleSheet, Text } from "react-native";
import { getInsights } from "../../src/api";
import { useData } from "../../src/data";
import { colors } from "../../src/theme";
import { Badge, Card, ErrorCard, Header, Loading, Screen } from "../../src/ui";

export default function InsightsScreen() {
  const { state } = useData();
  const [data, setData] = useState<Awaited<ReturnType<typeof getInsights>> | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { void load(); }, [state.dataset?.dataset_id, state.sessionId]);
  async function load() {
    if (!state.dataset || !state.sessionId) { setBusy(false); return; }
    setBusy(true); setError(null);
    try { setData(await getInsights(state.dataset.dataset_id, state.sessionId)); }
    catch (err) { setError(err instanceof Error ? err.message : "Insights could not be loaded."); }
    finally { setBusy(false); }
  }
  if (busy && !data) return <Screen><Loading /></Screen>;
  if (error) return <Screen><ErrorCard message={error} /></Screen>;
  if (!data) return <Screen><ErrorCard message="Choose a workspace with a dataset to continue." /></Screen>;
  return <Screen onRefresh={() => void load()} refreshing={busy}>
    <Header eyebrow={data.business_model_label || "INSIGHTS"} title={data.headline} subtitle={data.summary} />
    {data.insights.map(item => <Card key={item.id}>
      <Badge tone={item.severity === "high" ? "danger" : item.severity === "medium" ? "warning" : "neutral"}>{item.severity}</Badge>
      <Text style={styles.title}>{item.title}</Text>
      <Text style={styles.body}>{item.what_changed}</Text>
      <Text style={styles.why}>Why it matters: {item.why_it_matters}</Text>
      <Text style={styles.reco}>Recommendation: {item.recommendation}</Text>
      <Text style={styles.metric}>{item.metric}: {item.display_value}</Text>
      <Text style={styles.evidence}>{item.evidence.calculation}</Text>
    </Card>)}
  </Screen>;
}
const styles=StyleSheet.create({
  title:{fontSize:17,fontWeight:"800",color:colors.ink},
  body:{fontSize:13,lineHeight:20,color:"#5f6e82"},
  why:{fontSize:12,lineHeight:19,color:"#55657b"},
  reco:{fontSize:12,lineHeight:19,color:colors.accent},
  metric:{fontSize:12,fontWeight:"800",color:colors.ink},
  evidence:{fontSize:11,lineHeight:18,color:"#8a96a8"}
});