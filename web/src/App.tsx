import { packs } from "./data";
import { CustomerPage } from "./pages/CustomerPage";
import { Home } from "./pages/Home";
import { routeHref, useRoute } from "./routing";
import { Layout } from "./shell/Layout";
import { ThemeProvider } from "./theme/ThemeProvider";

export default function App() {
  // The URL decides the pack (and so the theme) and the customer.
  const { pack, customer, navigated } = useRoute(packs);

  return (
    <ThemeProvider theme={pack.theme}>
      <Layout homeHref={routeHref(pack.name)}>
        {customer === null ? (
          <Home pack={pack} packs={packs} navigated={navigated} />
        ) : (
          <CustomerPage pack={pack} customer={customer} navigated={navigated} />
        )}
      </Layout>
    </ThemeProvider>
  );
}
