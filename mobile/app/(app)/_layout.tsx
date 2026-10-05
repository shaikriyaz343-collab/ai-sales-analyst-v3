import { Ionicons } from "@expo/vector-icons";
import { Redirect, Tabs } from "expo-router";
import { useAuth } from "../../src/auth";
import { colors } from "../../src/theme";

export default function AppLayout() {
  const { state } = useAuth();
  if (state.loading) return null;
  if (!state.token) return <Redirect href="/sign-in" />;
  return (
    <Tabs screenOptions={{
      headerShown:false,
      tabBarActiveTintColor:colors.accent,
      tabBarInactiveTintColor:"#8794a7",
      tabBarLabelStyle:{fontSize:10,fontWeight:'700'},
      tabBarStyle:{height:68,paddingTop:6,paddingBottom:8,borderTopColor:colors.line,backgroundColor:'#fff'},
    }}>
      <Tabs.Screen name="overview" options={{title:"Overview",tabBarIcon:({color,size})=><Ionicons name="speedometer-outline" color={color} size={size}/>}}/>
      <Tabs.Screen name="decisions" options={{title:"Decisions",tabBarIcon:({color,size})=><Ionicons name="bulb-outline" color={color} size={size}/>}}/>
      <Tabs.Screen name="insights" options={{title:"Insights",tabBarIcon:({color,size})=><Ionicons name="analytics-outline" color={color} size={size}/>}}/>
      <Tabs.Screen name="ask" options={{title:"Ask",tabBarIcon:({color,size})=><Ionicons name="chatbubble-ellipses-outline" color={color} size={size}/>}}/>
      <Tabs.Screen name="monitoring" options={{title:"Monitor",tabBarIcon:({color,size})=><Ionicons name="notifications-outline" color={color} size={size}/>}}/>
      <Tabs.Screen name="more" options={{title:"More",tabBarIcon:({color,size})=><Ionicons name="ellipsis-horizontal-circle-outline" color={color} size={size}/>}}/>
      <Tabs.Screen name="workspace" options={{href:null}}/>
      <Tabs.Screen name="reports" options={{href:null}}/>
      <Tabs.Screen name="saved" options={{href:null}}/>
      <Tabs.Screen name="billing" options={{href:null}}/>
    </Tabs>
  );
}