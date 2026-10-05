import { useEffect, useState } from "react";
import { StyleSheet, Text } from "react-native";
import { evaluateAlerts, getAlerts } from "../../src/api";
import { useData } from "../../src/data";
import { registerDeviceForNotifications, syncLocalAlerts } from "../../src/notifications";
import { colors } from "../../src/theme";
import { Badge, Button, Card, ErrorCard, Header, Loading, Screen } from "../../src/ui";

export default function MonitoringScreen() {
  const { state } = useData();
  const [data,setData] = useState<Awaited<ReturnType<typeof getAlerts>> | null>(null);
  const [busy,setBusy] = useState(true);
  const [error,setError] = useState<string | null>(null);
  useEffect(() => { void load(true); }, [state.dataset?.dataset_id,state.sessionId]);
  async function load(evaluate:boolean) {
    if(!state.dataset || !state.sessionId){setBusy(false);return;}
    setBusy(true);setError(null);
    try {
      const result=evaluate ? await evaluateAlerts(state.dataset.dataset_id,state.sessionId) : await getAlerts(state.dataset.dataset_id,state.sessionId);
      setData(result);
      await registerDeviceForNotifications();
      await syncLocalAlerts().catch(() => 0);
    } catch(err) { setError(err instanceof Error ? err.message : "Monitoring could not be loaded."); }
    finally { setBusy(false); }
  }
  if(busy && !data)return <Screen><Loading /></Screen>;
  if(error && !data)return <Screen><ErrorCard message={error} /></Screen>;
  return <Screen onRefresh={() => void load(true)} refreshing={busy}>
    <Header eyebrow="MONITORING" title="Know when a signal changes" subtitle="Rules are evaluated from validated overview metrics. Device notifications are best-effort and controlled by the operating system." />
    <Button title={busy ? "Evaluating…" : "Evaluate now"} onPress={() => void load(true)} disabled={busy} />
    {error && <ErrorCard message={error} />}
    {data?.events.slice(0,10).map(event => <Card key={event.event_id}>
      <Badge tone={event.status === "triggered" ? "danger" : event.status === "clear" ? "success" : "warning"}>{event.status}</Badge>
      <Text style={styles.title}>{event.title}</Text>
      <Text style={styles.body}>{event.message}</Text>
      <Text style={styles.meta}>{event.evaluated_at} · {event.scope_label}</Text>
    </Card>)}
    {data?.events.length === 0 && <Card><Text style={styles.title}>No evaluations yet</Text><Text style={styles.body}>Create monitoring rules on the web app. Mobile will surface their latest results.</Text></Card>}
    {data?.rules.map(rule => <Card key={rule.rule_id}>
      <Badge tone={rule.active ? "success" : "neutral"}>{rule.cadence}</Badge>
      <Text style={styles.title}>{rule.name}</Text>
      <Text style={styles.body}>{rule.metric} {rule.operator} {rule.threshold}</Text>
      <Text style={styles.meta}>{rule.due ? "Due for evaluation" : "Next: " + (rule.next_due_at || "scheduled")}</Text>
    </Card>)}
  </Screen>;
}
const styles=StyleSheet.create({title:{fontSize:16,fontWeight:"800",color:colors.ink},body:{fontSize:13,lineHeight:20,color:"#5f6e82"},meta:{fontSize:10,color:"#8a96a8"}});