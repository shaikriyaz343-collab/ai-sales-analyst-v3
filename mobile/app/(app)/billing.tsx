import { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { getEntitlements } from "../../src/api";
import { colors } from "../../src/theme";
import { Badge, Card, ErrorCard, Header, Loading, Screen } from "../../src/ui";

export default function BillingScreen() {
  const [data,setData]=useState<Awaited<ReturnType<typeof getEntitlements>> | null>(null);
  const [busy,setBusy]=useState(true);
  const [error,setError]=useState<string|null>(null);
  useEffect(()=>{void load();},[]);
  async function load(){setBusy(true);setError(null);try{setData(await getEntitlements());}catch(err){setError(err instanceof Error?err.message:"Billing status could not be loaded.");}finally{setBusy(false);}}
  if(busy)return <Screen><Loading /></Screen>;
  if(error)return <Screen><ErrorCard message={error} /></Screen>;
  if(!data)return null;
  return <Screen onRefresh={()=>void load()} refreshing={busy}>
    <Header eyebrow="ACCOUNT & BILLING" title={data.plan.name} subtitle="Mobile shows entitlement state. Checkout and billing management remain web-based for this release." />
    <Card><Badge tone={data.access.status==="active"?"success":"warning"}>{data.access.status}</Badge><Text style={styles.price}>{data.plan.price_usd_monthly===0?"Free":"$"+data.plan.price_usd_monthly+"/month"}</Text><Text style={styles.body}>{data.access.trial?"Trial account":"Paid plan"}</Text>{data.access.trial_ends_at&&<Text style={styles.meta}>Trial ends {data.access.trial_ends_at}</Text>}</Card>
    <Card><Text style={styles.section}>Billing provider</Text><Text style={styles.body}>{data.billing.provider}</Text><Text style={styles.body}>Checkout ready: {data.billing.checkout_ready?"Yes":"No"}</Text><Text style={styles.body}>Customer portal: {data.billing.customer_portal_available?"Available":"Unavailable"}</Text></Card>
    <Card><Text style={styles.section}>Usage</Text>{Object.entries(data.usage).map(([key,value])=><View key={key} style={styles.usage}><Text style={styles.body}>{key.replaceAll("_"," ")}</Text><Text style={styles.usageValue}>{value.used} / {value.limit}</Text></View>)}</Card>
  </Screen>;
}
const styles=StyleSheet.create({price:{fontSize:30,fontWeight:"900",color:colors.ink},section:{fontSize:16,fontWeight:"800",color:colors.ink},body:{fontSize:13,lineHeight:20,color:"#5f6e82"},meta:{fontSize:11,color:"#8a96a8"},usage:{flexDirection:"row",justifyContent:"space-between",paddingVertical:6,borderBottomWidth:1,borderBottomColor:"#eef1f5"},usageValue:{fontSize:13,fontWeight:"800",color:colors.ink}});