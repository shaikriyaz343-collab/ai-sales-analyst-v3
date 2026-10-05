import { Redirect } from "expo-router";
import { useAuth } from "../src/auth";
import { Loading } from "../src/ui";

export default function Index() {
  const { state } = useAuth();
  if (state.loading) return <Loading />;
  return <Redirect href={state.token ? "/(app)/overview" : "/sign-in"} />;
}