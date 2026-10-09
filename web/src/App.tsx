import { packs } from "./data";
import { Layout } from "./shell/Layout";
import { ThemeProvider } from "./theme/ThemeProvider";

export default function App() {
  // Until Home lets you choose (5.6), show the first pack found.
  const pack = packs[0];

  return (
    <ThemeProvider theme={pack.theme}>
      <Layout>
        <h1>Explainer Engine</h1>
        <p>Your document, explained.</p>
      </Layout>
    </ThemeProvider>
  );
}
