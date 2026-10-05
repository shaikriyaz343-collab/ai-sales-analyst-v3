import { Linking, StyleSheet, Text } from "react-native";
import { router } from "expo-router";
import { useAuth } from "../../src/auth";
import { useData } from "../../src/data";
import { configureNotificationChannel, registerDeviceForNotifications } from "../../src/notifications";
import { colors } from "../../src/theme";
import { Button, Card, Header, Screen } from "../../src/ui";

export default function MoreScreen(){
 const {state:auth,signOut}=useAuth();
 const {state:data}=useData();
 async function enableNotifications(){await configureNotificationChannel();await registerDeviceForNotifications();}
 return <Screen><Header eyebrow="ACCOUNT" title={auth.user?.name||"Avenlytics"} subtitle={auth.user?.email}/>
  <Card><Text style={styles.section}>Workspace</Text><Text style={styles.body}>{data.user?.workspace_name||"Not selected"}</Text><Button title="Workspace selector" variant="secondary" onPress={()=>router.push("/(app)/workspace")}/></Card>
  <Card><Text style={styles.section}>Product</Text><Button title="Reports" variant="secondary" onPress={()=>router.push("/(app)/reports")}/><Button title="Saved intelligence" variant="secondary" onPress={()=>router.push("/(app)/saved")}/><Button title="Account & billing" variant="secondary" onPress={()=>router.push("/(app)/billing")}/></Card>
  <Card><Text style={styles.section}>Notifications</Text><Text style={styles.body}>Register this device for Avenlytics monitoring notifications.</Text><Button title="Enable notifications" variant="secondary" onPress={()=>void enableNotifications()}/></Card>
  <Card><Text style={styles.section}>Web app</Text><Text style={styles.body}>Use the web app for data uploads, creating monitoring rules, and billing actions.</Text><Button title="Open Avenlytics web" variant="secondary" onPress={()=>void Linking.openURL("https://peaceful-mindfulness-production-51b6.up.railway.app/")}/></Card>
  <Button title="Sign out" variant="danger" onPress={()=>void signOut().then(()=>router.replace("/sign-in"))}/>
 </Screen>;
}
const styles=StyleSheet.create({section:{fontSize:16,fontWeight:"800",color:colors.ink},body:{fontSize:13,lineHeight:20,color:"#5f6e82"}});