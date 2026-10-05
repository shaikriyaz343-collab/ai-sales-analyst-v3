import { useEffect, useState } from "react";
import { StyleSheet, Text, TextInput } from "react-native";
import { askAnalyst } from "../../src/api";
import { useData } from "../../src/data";
import { colors } from "../../src/theme";
import { Badge, Button, Card, ErrorCard, Header, Screen } from "../../src/ui";

export default function AskScreen() {
  const { state } = useData();
  const [question,setQuestion] = useState("");
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState<string | null>(null);
  const [answer,setAnswer] = useState<Awaited<ReturnType<typeof askAnalyst>> | null>(null);
  const suggestions = ["What changed most recently?","Which customers need attention?","What supports the current pipeline signal?"];
  useEffect(() => { setAnswer(null); setQuestion(""); setError(null); }, [state.dataset?.dataset_id,state.sessionId]);
  async function submit(value?:string) {
    const q=(value ?? question).trim();
    if(!state.dataset || !state.sessionId || !q) return;
    setBusy(true); setError(null);
    try { setAnswer(await askAnalyst(state.dataset.dataset_id,q,state.sessionId)); setQuestion(q); }
    catch(err) { setError(err instanceof Error ? err.message : "The analyst could not answer that question."); }
    finally { setBusy(false); }
  }
  if(!state.dataset || !state.sessionId) return <Screen><ErrorCard message="Choose a workspace with a dataset to ask the analyst." /></Screen>;
  return <Screen>
    <Header eyebrow="ASK ANALYST" title="Ask about the current data" subtitle="Answers stay within what the validated dataset supports." />
    <TextInput value={question} onChangeText={setQuestion} placeholder="Ask a question…" placeholderTextColor="#99a5b5" multiline onSubmitEditing={() => void submit()} style={styles.input} />
    <Button title={busy ? "Analyzing…" : "Ask Analyst"} onPress={() => void submit()} disabled={busy || !question.trim()} />
    {suggestions.map(q => <Button key={q} title={q} variant="secondary" onPress={() => void submit(q)} disabled={busy} />)}
    {error && <ErrorCard message={error} />}
    {answer && <Card>
      <Badge tone={answer.answer.status === "unsupported" ? "danger" : "success"}>{answer.answer.status}</Badge>
      <Text style={styles.answer}>{answer.answer.text}</Text>
      {answer.answer.evidence && <Text style={styles.evidence}>{answer.answer.evidence.calculation} · {answer.answer.evidence.scope}</Text>}
      {answer.follow_ups.map(f => <Text key={f.question} style={styles.followup} onPress={() => void submit(f.question)}>Try: {f.label}</Text>)}
    </Card>}
  </Screen>;
}
const styles=StyleSheet.create({
  input:{minHeight:120,backgroundColor:"#fff",borderWidth:1,borderColor:colors.line,borderRadius:14,padding:14,textAlignVertical:"top",fontSize:15,color:colors.ink},
  answer:{fontSize:17,lineHeight:25,color:colors.ink},
  evidence:{fontSize:11,lineHeight:18,color:"#7b8798"},
  followup:{fontSize:12,fontWeight:"800",color:colors.accent,paddingTop:4}
});