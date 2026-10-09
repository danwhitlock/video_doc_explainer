import { packs } from "./data";
import { useRoute } from "./routing";
import { Layout } from "./shell/Layout";
import { ThemeProvider } from "./theme/ThemeProvider";

export default function App() {
  // The URL decides the pack (and so the theme) and the customer.
  const { pack, customer } = useRoute(packs);

  return (
    <ThemeProvider theme={pack.theme}>
      <Layout>
        {/* Temporary, to show routing working; replaced by Home (5.6b) and the Player (5.7+). */}
        <h1>{customer === null ? `Home for ${pack.theme.brand.name}` : `Explainer for ${customer.preferred_name}`}</h1>
      </Layout>
    </ThemeProvider>
  );
}
