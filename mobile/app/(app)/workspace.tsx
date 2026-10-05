import { StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { useData } from "../../src/data";
import { colors } from "../../src/theme";
import { Badge, Button, Card, ErrorCard, Header, Loading, Screen } from "../../src/ui";

export default function WorkspaceScreen(){
 const {state,selectWorkspace}=useData();
 if(state.loading)return <Screen><Loading /></Screen>;
 if(!state.user)return <Screen><ErrorCard message="Your organization could not be loaded." /></Screen>;
 return <Screen><Header eyebrow="WORKSPACE SELECTOR" title="Choose where to work" subtitle="Each workspace keeps its own current dataset and analytical session." />{state.user.workspaces.map(w=>{const current=w.id===state.workspaceId;const dataset=state.datasets[w.id];return <Card key={w.id}><View style={styles.row}><View style={styles.grow}><Text style={styles.title}>{w.name}</Text><Text style={styles.meta}>{dataset?.file_name||"No dataset loaded"}</Text></View>{current&&<Badge tone="success">Current</Badge>}</View><Button title={current?"Current workspace":"Open workspace"} variant={current?"secondary":"primary"} onPress={()=>void selectWorkspace(w.id).then(()=>router.replace("/(app)/overview"))} disabled={current}/></Card>})}</Screen>;
}
const styles=StyleSheet.create({row:{flexDirection:"row",alignItems:"center",gap:10},grow:{flex:1},title:{fontSize:16,fontWeight:"800",color:colors.ink},meta:{fontSize:11,color:"#8a96a8",marginTop:3}});