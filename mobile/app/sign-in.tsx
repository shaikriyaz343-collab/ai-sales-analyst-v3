import { useState } from "react";
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { router } from "expo-router";
import { useAuth } from "../src/auth";
import { colors } from "../src/theme";
import { Button, ErrorCard } from "../src/ui";

export default function SignInScreen() {
  const { signIn, signUp } = useAuth();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [name, setName] = useState("");
  const [organization, setOrganization] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setBusy(true); setError(null);
    try {
      if (mode === "signup") await signUp(email, password, name, organization || "My Organization");
      else await signIn(email, password);
      router.replace("/(app)/overview");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed.");
    } finally { setBusy(false); }
  }

  return (
    <KeyboardAvoidingView style={styles.root} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <View style={styles.brand}>
          <View style={styles.mark}><Text style={styles.markText}>A</Text></View>
          <View><Text style={styles.brandName}>Avenlytics</Text><Text style={styles.brandSub}>AI Sales Analyst</Text></View>
        </View>
        <Text style={styles.eyebrow}>{mode === "signin" ? "WELCOME BACK" : "START YOUR REVENUE WORKSPACE"}</Text>
        <Text style={styles.title}>{mode === "signin" ? "See what changed." : "Give your sales data an analyst."}</Text>
        <Text style={styles.subtitle}>{mode === "signin" ? "Sign in to the same Avenlytics workspace you use on the web." : "Create your Avenlytics account. Mobile uses the same organization data as the web product."}</Text>
        {mode === "signup" && <><Field label="Name" value={name} onChangeText={setName} autoCapitalize="words" /><Field label="Organization" value={organization} onChangeText={setOrganization} autoCapitalize="words" /></>}
        <Field label="Email" value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" />
        <Field label="Password" value={password} onChangeText={setPassword} secureTextEntry />
        {error && <ErrorCard message={error} />}
        <Button title={busy ? (mode === "signin" ? "Signing in…" : "Creating account…") : mode === "signin" ? "Sign in" : "Create account"} onPress={() => void submit()} disabled={busy || !email || !password || (mode === "signup" && !name)} />
        <Button title={mode === "signin" ? "Create a new account" : "I already have an account"} variant="ghost" onPress={() => { setMode(mode === "signin" ? "signup" : "signin"); setError(null); }} disabled={busy} />
        <Text style={styles.trust}>Analytics stay grounded in the validated sales data available to your organization. Avenlytics will not invent unsupported numbers.</Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function Field(props: React.ComponentProps<typeof TextInput> & { label: string }) {
  const { label, ...input } = props;
  return <View style={styles.field}><Text style={styles.label}>{label}</Text><TextInput {...input} placeholder={label} placeholderTextColor="#99a5b5" style={styles.input} /></View>;
}

const styles = StyleSheet.create({
  root:{flex:1,backgroundColor:colors.bg},
  content:{padding:24,paddingTop:64,paddingBottom:48,gap:14},
  brand:{flexDirection:'row',alignItems:'center',gap:10,marginBottom:36},
  mark:{width:40,height:40,borderRadius:12,backgroundColor:'#102039',alignItems:'center',justifyContent:'center'},
  markText:{color:'#fff',fontWeight:'900',fontSize:18},
  brandName:{fontSize:16,fontWeight:'900',color:colors.ink},
  brandSub:{fontSize:11,color:colors.muted,marginTop:2},
  eyebrow:{fontSize:10,fontWeight:'900',letterSpacing:1.2,color:'#7e8ba0'},
  title:{fontSize:34,fontWeight:'900',lineHeight:39,letterSpacing:-1,color:colors.ink},
  subtitle:{fontSize:14,lineHeight:21,color:colors.muted,marginBottom:8},
  field:{gap:7},label:{fontSize:12,fontWeight:'800',color:colors.ink},
  input:{backgroundColor:'#fff',borderWidth:1,borderColor:colors.line,borderRadius:12,paddingHorizontal:14,minHeight:48,fontSize:15,color:colors.ink},
  trust:{fontSize:11,lineHeight:17,color:'#7d899b',marginTop:8}
});