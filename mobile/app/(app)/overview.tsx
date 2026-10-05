import { useEffect, useState } from "react";
import { Linking, Pressable, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { getOverview } from "../../src/api";
import { useData } from "../../src/data";
import { colors } from "../../src/theme";
import { Badge, Card, Empty, ErrorCard, Header, Loading, MetricCard, Screen } from "../../src/ui";
import { configureNotificationChannel, registerDeviceForNotifications, syncLocalAlerts } from "../../src/notifications";
import { registerAlertBackgroundTask } from "../../src/background";

export default function OverviewScreen() {
  const { state, refresh } = useData();
  const [data, setData] = useState<Awaited<ReturnType<typeof getOverview>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { void load(); }, [state.dataset?.dataset_id, state.sessionId]);
  async function load() {
    if (!state.dataset || !state.sessionId) { setLoading(false); setData(null); return; }
    setLoading(true); setError(null);
    try {
      setData(await getOverview(state.dataset.dataset_id, state.sessionId));
      await configureNotificationChannel();
      await registerDeviceForNotifications();
      await registerAlertBackgroundTask();
      await syncLocalAlerts().catch(() => 0);
    } catch (err) { setError(err instanceof Error ? err.message : "Overview could not be loaded."); }
    finally { setLoading(false); }
  }

  if (state.loading || loading) return <Screen><Loading /></Screen>;
  if (state.error) return <Screen><ErrorCard message={state.error} /></Screen>;
  if (error) return <Screen onRefresh={() => void load()}><ErrorCard message={error} /></Screen>;
  if (!state.dataset || !state.sessionId) return <Screen onRefresh={() => void refresh()}><Header eyebrow={state.user?.organization_name} title="Your revenue workspace" subtitle="Mobile uses the same workspace data as the web app." /><Empty title="No dataset is ready here" body="Upload your CSV or XLSX from the Avenlytics web app, then return to mobile." action={<Pressable style={styles.webButton} onPress={() => void Linking.openURL("https://peaceful-mindfulness-production-51b6.up.railway.app/")}><Text style={styles.webButtonText}>Open Avenlytics web</Text></Pressable>} /><Card><Text style={styles.cardTitle}>Current workspace</Text><Text style={styles.body}>{state.user?.workspace_name ?? "Choose a workspace"}</Text><Pressable onPress={() => router.push("/(app)/workspace")}><Text style={styles.link}>Switch workspace →</Text></Pressable></Card></Screen>;
  if (!data) return null;
  return <Screen onRefresh={() => void load()} refreshing={loading}>
    <Header eyebrow={state.user?.organization_name} title={data.headline} subtitle={data.subheadline} />
    <View style={styles.contextRow}><View><Text style={styles.contextLabel}>{state.user?.workspace_name}</Text><Text style={styles.contextFile}>{state.dataset.file_name}</Text></View><Pressable onPress={() => router.push("/(app)/workspace")}><Badge>Switch</Badge></Pressable></View>
    <Badge tone={state.dataset.quality_issues > 0 ? "warning" : "success"}>{state.dataset.quality_issues > 0 ? String(state.dataset.quality_issues) + " data-quality findings" : "Validated dataset"}</Badge>
    <View style={styles.metrics}>{data.metrics.slice(0, 4).map(metric => <MetricCard key={metric.id} label={metric.label} value={metric.display_value} detail={metric.delta_label || metric.evidence.calculation} />)}</View>
    <Card><Text style={styles.cardTitle}>What changed</Text>{data.what_changed.slice(0, 5).map(item => <Text key={item} style={styles.bullet}>• {item}</Text>)}</Card>
    {data.attention.slice(0, 4).map(item => <Card key={item.id}><View style={styles.cardTop}><Badge tone={item.severity === "high" ? "danger" : item.severity === "medium" ? "warning" : "neutral"}>{item.severity}</Badge><Text style={styles.meta}>Attention</Text></View><Text style={styles.cardTitle}>{item.title}</Text><Text style={styles.body}>{item.summary}</Text><Text style={styles.reco}>Next: {item.recommendation}</Text></Card>)}
    {data.opportunities.slice(0, 3).map(item => <Card key={item.id}><Badge tone="success">Opportunity</Badge><Text style={styles.cardTitle}>{item.title}</Text><Text style={styles.body}>{item.summary}</Text></Card>)}
  </Screen>;
}

const styles=StyleSheet.create({
  contextRow:{flexDirection:"row",justifyContent:"space-between",alignItems:"center",gap:10},
  contextLabel:{fontSize:14,fontWeight:"800",color:colors.ink},
  contextFile:{fontSize:11,color:colors.muted,marginTop:2},
  metrics:{gap:10},
  cardTitle:{fontSize:16,fontWeight:"800",color:colors.ink},
  bullet:{fontSize:13,lineHeight:20,color:"#58677c"},
  cardTop:{flexDirection:"row",justifyContent:"space-between",alignItems:"center"},
  meta:{fontSize:11,color:"#8b97a8"},
  body:{fontSize:13,lineHeight:20,color:"#5f6e82"},
  reco:{fontSize:12,lineHeight:19,color:"#2e5bba"},
  webButton:{marginTop:8,minHeight:44,borderRadius:11,backgroundColor:colors.accent,justifyContent:"center",alignItems:"center"},
  webButtonText:{color:"#fff",fontWeight:"800",fontSize:13},
  link:{fontSize:12,fontWeight:"800",color:colors.accent,marginTop:4}
});