import { ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";
import { colors } from "./theme";

export function Screen({children, onRefresh, refreshing=false}:{children:React.ReactNode;onRefresh?:()=>void;refreshing?:boolean}) {
  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
      refreshControl={onRefresh ? <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.accent} /> : undefined}
    >
      {children}
    </ScrollView>
  );
}

export function Header({eyebrow,title,subtitle}:{eyebrow?:string;title:string;subtitle?:string}) {
  return <View style={styles.header}>{eyebrow && <Text style={styles.eyebrow}>{eyebrow}</Text>}<Text style={styles.title}>{title}</Text>{subtitle && <Text style={styles.subtitle}>{subtitle}</Text>}</View>;
}
export function Card({children,style}:{children:React.ReactNode;style?:object}) { return <View style={[styles.card,style]}>{children}</View>; }
export function MetricCard({label,value,detail}:{label:string;value:string;detail?:string}) {
  return <Card><Text style={styles.metricLabel}>{label}</Text><Text style={styles.metricValue}>{value}</Text>{detail && <Text style={styles.metricDetail}>{detail}</Text>}</Card>;
}
export function Button({title,onPress,variant="primary",disabled=false}:{title:string;onPress:()=>void;variant?: "primary"|"secondary"|"danger"|"ghost";disabled?:boolean}) {
  return <Pressable onPress={onPress} disabled={disabled} style={({pressed})=>[styles.button,variant==="secondary"&&styles.buttonSecondary,variant==="danger"&&styles.buttonDanger,variant==="ghost"&&styles.buttonGhost,pressed&&styles.pressed,disabled&&styles.disabled]}><Text style={[styles.buttonText,variant==="secondary"&&styles.buttonTextSecondary,variant==="danger"&&styles.buttonTextDanger,variant==="ghost"&&styles.buttonTextGhost]}>{title}</Text></Pressable>;
}
export function Loading() { return <View style={styles.loading}><ActivityIndicator color={colors.accent}/><Text style={styles.loadingText}>Loading your revenue workspace…</Text></View>; }
export function ErrorCard({message}:{message:string}) { return <Card style={styles.errorCard}><Text style={styles.errorTitle}>Could not load this view</Text><Text style={styles.errorText}>{message}</Text></Card>; }
export function Empty({title,body,action}:{title:string;body:string;action?:React.ReactNode}) { return <Card><Text style={styles.emptyTitle}>{title}</Text><Text style={styles.emptyBody}>{body}</Text>{action}</Card>; }
export function Badge({children, tone="neutral"}:{children:React.ReactNode;tone?: "neutral"|"success"|"danger"|"warning"}) {
  return <View style={[styles.badge,tone==="success"&&styles.badgeSuccess,tone==="danger"&&styles.badgeDanger,tone==="warning"&&styles.badgeWarning]}><Text style={styles.badgeText}>{children}</Text></View>;
}
export function SectionTitle({label,title}:{label?:string;title:string}) {
  return <View style={styles.sectionTitle}>{label && <Text style={styles.eyebrow}>{label}</Text>}<Text style={styles.sectionHeading}>{title}</Text></View>;
}
export const styles=StyleSheet.create({
  screen:{flex:1,backgroundColor:colors.bg},
  content:{padding:20,paddingTop:16,paddingBottom:40,gap:16},
  header:{gap:6,marginBottom:2},
  eyebrow:{fontSize:11,fontWeight:"800",letterSpacing:1.2,color:"#8a96a8"},
  title:{fontSize:30,lineHeight:35,fontWeight:"800",letterSpacing:-0.7,color:colors.ink},
  subtitle:{fontSize:14,lineHeight:20,color:colors.muted},
  card:{backgroundColor:colors.panel,borderRadius:16,borderWidth:1,borderColor:colors.line,padding:16,gap:8},
  metricLabel:{fontSize:12,color:colors.muted},
  metricValue:{fontSize:28,fontWeight:"800",color:colors.ink},
  metricDetail:{fontSize:12,color:colors.muted,lineHeight:17},
  button:{minHeight:46,borderRadius:12,justifyContent:"center",alignItems:"center",paddingHorizontal:16,backgroundColor:colors.accent},
  buttonSecondary:{backgroundColor:colors.panel,borderWidth:1,borderColor:"#cfd8e8"},
  buttonDanger:{backgroundColor:"#fff1f0",borderWidth:1,borderColor:"#f0c2c2"},
  buttonGhost:{backgroundColor:"transparent"},
  buttonText:{fontSize:14,fontWeight:"800",color:"#fff"},
  buttonTextSecondary:{color:colors.ink},
  buttonTextDanger:{color:colors.danger},
  buttonTextGhost:{color:colors.accent},
  pressed:{opacity:0.78},disabled:{opacity:0.5},
  loading:{padding:56,alignItems:"center",gap:12},loadingText:{color:colors.muted,fontSize:13},
  errorCard:{backgroundColor:"#fff7f7",borderColor:"#f0c2c2"},errorTitle:{fontSize:15,fontWeight:"800",color:colors.danger},errorText:{fontSize:13,lineHeight:19,color:"#7a2b2b"},
  emptyTitle:{fontSize:18,fontWeight:"800",color:colors.ink},emptyBody:{fontSize:13,lineHeight:20,color:colors.muted},
  badge:{alignSelf:"flex-start",paddingHorizontal:9,paddingVertical:5,borderRadius:999,backgroundColor:"#eef2f7"},
  badgeText:{fontSize:11,fontWeight:"800",color:"#55657b"},
  badgeSuccess:{backgroundColor:"#eaf7f0"},badgeDanger:{backgroundColor:"#fff0ee"},badgeWarning:{backgroundColor:"#fff6dd"},
  sectionTitle:{gap:4},sectionHeading:{fontSize:20,fontWeight:"800",color:colors.ink}
});
