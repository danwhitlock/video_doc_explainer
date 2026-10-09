import { packs } from "./data";
import { Home } from "./pages/Home";
import { useRoute } from "./routing";
import { Layout } from "./shell/Layout";
import { ThemeProvider } from "./theme/ThemeProvider";

export default function App() {
  // The URL decides the pack (and so the theme) and the customer.
  const { pack, customer } = useRoute(packs);

  return (
    <ThemeProvider theme={pack.theme}>
      <Layout>
        {customer === null ? (
          <Home pack={pack} packs={packs} />
        ) : (
          // Temporary: replaced by a proper customer page (5.6c) and the Player (5.7+).
          <h1>Explainer for {customer.preferred_name}</h1>
        )}
      </Layout>
    </ThemeProvider>
  );
}
