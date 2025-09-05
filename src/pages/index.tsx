import type {ReactNode} from 'react';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout title={siteConfig.title} description={siteConfig.tagline}>
      <main style={{padding: '4rem 0'}}>
        <div className="container" style={{textAlign: 'center'}}>
          <h1 style={{marginBottom: '0.5rem'}}>{siteConfig.title}</h1>
          <p>{siteConfig.tagline}</p>
          <div style={{marginTop: '2rem'}}>
            <Link className="button button--primary button--lg" to="/resume">
              View Resume
            </Link>
          </div>
        </div>
      </main>
    </Layout>
  );
}
