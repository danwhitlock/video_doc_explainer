import { packs } from "./data";
import { ThemeProvider } from "./theme/ThemeProvider";

export default function App() {
  // Until Home lets you choose (5.6), show the first pack found.
  const pack = packs[0];

  return (
    <ThemeProvider theme={pack.theme}>
      <main>
        <h1>Explainer Engine</h1>
        <p>Your document, explained.</p>
      </main>
      <footer>
        <p>Fictional demonstrator — not financial or medical advice</p>
      </footer>
    </ThemeProvider>
  );
}
