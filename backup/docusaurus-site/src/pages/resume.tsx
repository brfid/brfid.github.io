import type {ReactNode} from 'react';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
import clsx from 'clsx';
import styles from './resume.module.css';
import data from '@site/src/data/resume.json';

type Basics = {
  name?: string;
  label?: string;
  email?: string;
  phone?: string;
  summary?: string;
  url?: string;
  location?: {city?: string; region?: string; countryCode?: string};
  profiles?: {network?: string; username?: string; url?: string}[];
};

type Work = {
  name?: string; // company
  position?: string;
  url?: string;
  location?: string;
  startDate?: string;
  endDate?: string;
  summary?: string;
  highlights?: string[];
};

type Education = {
  institution?: string;
  area?: string;
  studyType?: string;
  startDate?: string;
  endDate?: string;
  score?: string;
};

type Certificate = {
  name?: string;
  date?: string;
  issuer?: string;
  url?: string;
};

type Publication = {
  name?: string;
  publisher?: string;
  releaseDate?: string;
  url?: string;
  summary?: string;
};

type Skill = {name?: string; level?: string; keywords?: string[]};
type Language = {language?: string; fluency?: string};
type Interest = {name?: string; keywords?: string[]};
type Volunteer = {organization?: string; position?: string; startDate?: string; endDate?: string; summary?: string};
type Project = {name?: string; description?: string; startDate?: string; endDate?: string; url?: string; entity?: string; keywords?: string[]};

type Resume = {
  basics?: Basics;
  work?: Work[];
  education?: Education[];
  certificates?: Certificate[];
  publications?: Publication[];
  skills?: Skill[];
  languages?: Language[];
  interests?: Interest[];
  volunteer?: Volunteer[];
  projects?: Project[];
  [k: string]: unknown;
};

const resume = data as Resume;

function formatDate(d?: string): string | undefined {
  if (!d) return undefined;
  // Accept YYYY, YYYY-MM, or YYYY-MM-DD
  const parts = d.split('-').map((p) => parseInt(p, 10));
  const [y, m] = [parts[0], parts[1] ?? 1];
  if (!y || y < 1900 || y > 3000) return d;
  const date = new Date(Date.UTC(y, Math.max(0, m - 1), 1));
  return date.toLocaleString('en-US', {month: 'short', year: 'numeric'});
}

function range(start?: string, end?: string): string | undefined {
  const s = formatDate(start);
  const e = end ? formatDate(end) : undefined;
  
  // If neither start nor end date provided, show nothing
  if (!start && !end) return undefined;
  
  // If start but no end, show "Start — Present"
  if (s && !e) return `${s} — Present`;
  
  // If both start and end, show "Start — End" 
  if (s && e) return `${s} — ${e}`;
  
  // Fallback (shouldn't normally reach here)
  return s ?? e;
}

function Section({id, title, children, hideTitle = false}: {id: string; title: string; children: ReactNode; hideTitle?: boolean}) {
  return (
    <section id={id} className={styles.section}>
      {!hideTitle && <h2 className={styles.sectionTitle}>{title}</h2>}
      <div>{children}</div>
    </section>
  );
}

function SideToc({sections}: {sections: {id: string; title: string}[]}) {
  return (
    <nav className={styles.toc} aria-label="Resume sections">
      <ul>
        {sections.map((s) => (
          <li key={s.id}>
            <a href={`#${s.id}`}>{s.title}</a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

export default function ResumePage(): ReactNode {
  const leftSections: {id: string; title: string; render: () => ReactNode}[] = [];
  const rightSections: {id: string; title: string; render: () => ReactNode}[] = [];
  const fullWidthSections: {id: string; title: string; render: () => ReactNode}[] = [];

  const b = resume.basics;
  const work = resume.work ?? [];
  const edu = resume.education ?? [];
  const certs = resume.certificates ?? [];
  const pubs = resume.publications ?? [];
  const skills = resume.skills ?? [];
  const langs = resume.languages ?? [];
  const interests = resume.interests ?? [];
  const volunteer = resume.volunteer ?? [];
  const projects = resume.projects ?? [];

  if (b?.summary) {
    leftSections.push({
      id: 'summary',
      title: 'Professional Summary',
      render: () => (
        <div className={styles.card}>
          <p className={styles.lead}>{b.summary}</p>
        </div>
      ),
    });
  }

  // Skills in right column
  if (skills.length) {
    rightSections.push({
      id: 'skills',
      title: 'Technical Skills',
      render: () => (
        <div className={styles.skillGrid}>
          {skills.map((s, i) => (
            <div key={i} className={clsx(styles.skillBlock, styles.card)}>
              <div className={styles.skillHeader}>
                <strong>{s.name}</strong>
                {s.level && <span className={styles.meta}>{s.level}</span>}
              </div>
              {s.keywords?.length ? (
                <div className={styles.tags}>
                  {s.keywords.map((k, idx) => (
                    <span key={idx} className={styles.tag}>{k}</span>
                  ))}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      ),
    });
  }

  if (work.length) {
    leftSections.push({
      id: 'experience',
      title: 'Experience',
      render: () => (
        <div className={styles.listStack}>
          {work.map((w, i) => (
            <article key={i} className={styles.card}>
              <header className={styles.cardHeader}>
                <div className={styles.cardPrimaryLine}>
                  <strong>{w.position}</strong>
                  {w.name ? (
                    <>
                      {' '}
                      <span className={styles.at}>@</span>{' '}
                      {w.url ? (
                        <a href={w.url} target="_blank" rel="noreferrer noopener">{w.name}</a>
                      ) : (
                        <span>{w.name}</span>
                      )}
                    </>
                  ) : null}
                </div>
                <div className={styles.metaLine}>
                  {range(w.startDate, w.endDate) && (
                    <span className={styles.meta}>{range(w.startDate, w.endDate)}</span>
                  )}
                  {w.location && <span className={styles.meta}>{w.location}</span>}
                </div>
              </header>
              {w.summary && <p className={styles.body}>{w.summary}</p>}
              {w.highlights?.length ? (
                <ul className={styles.bullets}>
                  {w.highlights.map((h, idx) => (
                    <li key={idx}>{h}</li>
                  ))}
                </ul>
              ) : null}
            </article>
          ))}
        </div>
      ),
    });
  }

  if (projects.length) {
    rightSections.push({
      id: 'projects',
      title: 'Projects',
      render: () => (
        <div className={styles.gridCards}>
          {projects.map((p, i) => (
            <article key={i} className={styles.card}>
              <header className={styles.cardHeader}>
                <div className={styles.cardPrimaryLine}>
                  <strong>{p.name}</strong>
                </div>
                <div className={styles.metaLine}>
                  {p.entity && <span className={styles.meta}>{p.entity}</span>}
                  {range(p.startDate, p.endDate) && (
                    <span className={styles.meta}>{range(p.startDate, p.endDate)}</span>
                  )}
                </div>
              </header>
              {p.description && <p className={styles.body}>{p.description}</p>}
              {p.keywords?.length ? (
                <div className={styles.tags}>
                  {p.keywords.map((k, idx) => (
                    <span key={idx} className={styles.tag}>{k}</span>
                  ))}
                </div>
              ) : null}
              {p.url && (
                <p className={styles.linkLine}>
                  <Link to={p.url}>Project link</Link>
                </p>
              )}
            </article>
          ))}
        </div>
      ),
    });
  }

  // Skills section moved to top after summary for FAANG optimization

  if (edu.length) {
    rightSections.push({
      id: 'education',
      title: 'Education',
      render: () => (
        <div className={styles.listStack}>
          {edu.map((e, i) => (
            <article key={i} className={styles.card}>
              <header className={styles.cardHeader}>
                <div className={styles.cardPrimaryLine}>
                  <strong>{e.institution}</strong>
                </div>
                <div className={styles.metaLine}>
                  {[e.studyType, e.area].filter(Boolean).join(', ') && (
                    <span className={styles.meta}>{[e.studyType, e.area].filter(Boolean).join(', ')}</span>
                  )}
                  {range(e.startDate, e.endDate) && (
                    <span className={styles.meta}>{range(e.startDate, e.endDate)}</span>
                  )}
                  {e.score && <span className={styles.meta}>GPA {e.score}</span>}
                </div>
              </header>
            </article>
          ))}
        </div>
      ),
    });
  }

  if (certs.length) {
    rightSections.push({
      id: 'certificates',
      title: 'Certificates',
      render: () => (
        <div className={styles.card}>
          <ul className={styles.simpleList}>
            {certs.map((c, i) => (
              <li key={i}>
                <strong>{c.name}</strong>
                {c.issuer ? <> — {c.issuer}</> : null}
                {c.date ? <> ({formatDate(c.date)})</> : null}
                {c.url ? (
                  <>
                    {' '}
                    <a href={c.url} target="_blank" rel="noreferrer noopener">link</a>
                  </>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ),
    });
  }

  if (pubs.length) {
    leftSections.push({
      id: 'publications',
      title: 'Publications',
      render: () => (
        <div className={styles.card}>
          <ul className={styles.publicationsList}>
            {pubs.map((p, i) => (
              <li key={i} className={styles.publicationItem}>
                <strong>{p.name}</strong>
                {p.publisher && p.url ? (
                  <>
                    {' — '}
                    <a href={p.url} target="_blank" rel="noreferrer noopener" className={styles.pubLink}>
                      {p.publisher}
                    </a>
                  </>
                ) : (
                  p.publisher && <> — {p.publisher}</>
                )}
                {p.releaseDate && <> ({formatDate(p.releaseDate)})</>}
              </li>
            ))}
          </ul>
        </div>
      ),
    });
  }

  if (volunteer.length) {
    rightSections.push({
      id: 'volunteer',
      title: 'Volunteer',
      render: () => (
        <div className={styles.card}>
          <ul className={styles.simpleList}>
            {volunteer.map((v, i) => (
              <li key={i}>
                <strong>{v.organization}</strong>
                {v.position ? <> — {v.position}</> : null}
                {(v.startDate || v.endDate) ? <> — {range(v.startDate, v.endDate)}</> : null}
                {v.summary ? <> — {v.summary}</> : null}
              </li>
            ))}
          </ul>
        </div>
      ),
    });
  }

  if (langs.length) {
    rightSections.push({
      id: 'languages',
      title: 'Languages',
      render: () => (
        <div className={styles.card}>
          <ul className={styles.simpleList}>
            {langs.map((l, i) => (
              <li key={i}>
                <strong>{l.language}</strong>
                {l.fluency ? <> — {l.fluency}</> : null}
              </li>
            ))}
          </ul>
        </div>
      ),
    });
  }

  if (interests.length) {
    rightSections.push({
      id: 'interests',
      title: 'Interests',
      render: () => (
        <div className={styles.card}>
          <div className={styles.tags}>
            {interests.flatMap((it) => [it.name, ...(it.keywords ?? [])]).filter(Boolean).map((k, i) => (
              <span key={i} className={styles.tag}>{k}</span>
            ))}
          </div>
        </div>
      ),
    });
  }

  // Build contact block from basics - optimized for print, no duplicates
  const contacts: {label: string; value?: string; href?: string}[] = [];
  if (b?.email) contacts.push({label: 'Email', value: b.email, href: `mailto:${b.email}`});
  if (b?.phone) contacts.push({label: 'Phone', value: b.phone, href: `tel:${b.phone}`});
  
  // Add unique profiles only
  const seenNetworks = new Set<string>();
  (b?.profiles ?? []).forEach((p) => {
    if (p?.url && p?.network && !seenNetworks.has(p.network)) {
      seenNetworks.add(p.network);
      const displayValue = p.network === 'LinkedIn' ? `linkedin.com/in/${p.username}` : 
                          p.network === 'GitHub' ? `github.com/${p.username}` :
                          p.username ?? p.url;
      contacts.push({label: p.network, value: displayValue, href: p.url});
    }
  });
  
  // Add header as first section in left column for print
  leftSections.unshift({
    id: 'header',
    title: b?.name || 'Resume',
    render: () => (
      <div className={clsx(styles.headerSection, styles.printOnly)}>
        {b?.name && <h1 className={styles.printName}>{b.name}</h1>}
        {b?.label && <p className={styles.printTitle}>{b.label}</p>}
        {(b?.location?.city || b?.location?.region || b?.location?.countryCode) && (
          <p className={styles.printLocation}>
            {[b?.location?.city, b?.location?.region, b?.location?.countryCode]
              .filter(Boolean)
              .join(', ')}
          </p>
        )}
        {contacts.length > 0 && (
          <div className={styles.printContact}>
            {contacts.map((c, i) => (
              <span key={i} className={styles.contactItem}>
                {c.href ? (
                  <a href={c.href} target="_blank" rel="noreferrer noopener">{c.value}</a>
                ) : (
                  <span>{c.value}</span>
                )}
              </span>
            ))}
          </div>
        )}
      </div>
    ),
  });

  return (
    <Layout title="Resume" description="Resume">
      <main className={clsx('container', styles.page)}>
        <aside className={styles.side}>
          {/* Screen-only header and contact */}
          {b?.name || b?.label ? (
            <div className={clsx(styles.headerCard, styles.screenOnly)}>
              {b?.name && <h1 className={styles.name}>{b.name}</h1>}
              {b?.label && <p className={styles.title}>{b.label}</p>}
              {(b?.location?.city || b?.location?.region || b?.location?.countryCode) && (
                <p className={styles.location}>
                  {[b?.location?.city, b?.location?.region, b?.location?.countryCode]
                    .filter(Boolean)
                    .join(', ')}
                </p>
              )}
            </div>
          ) : null}

          {contacts.length ? (
            <div className={clsx(styles.contactCard, styles.screenOnly)}>
              <h2 className={styles.sectionTitleSm}>Contact</h2>
              <ul className={styles.contactList}>
                {contacts.map((c, i) => (
                  <li key={i}>
                    <span className={styles.contactLabel}>{c.label}</span>
                    {c.href ? (
                      <a href={c.href} target="_blank" rel="noreferrer noopener">{c.value}</a>
                    ) : (
                      <span>{c.value}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {/* Print TOC for screen only */}
          <div className={styles.screenOnly}>
            {(leftSections.length + rightSections.length) > 1 && (
              <SideToc sections={[
                ...leftSections.slice(1).map(({id, title}) => ({id, title})), // Skip header section
                ...rightSections.map(({id, title}) => ({id, title}))
              ]} />
            )}
          </div>
        </aside>

        <div className={styles.main}>
          {/* Two column layout */}
          <div className={styles.main}>
            <div className={styles.mainColumn}>
              {leftSections.map((s, index) => (
                <Section key={s.id} id={s.id} title={s.title} hideTitle={index === 0}>
                  {s.render()}
                </Section>
              ))}
            </div>
            <div className={styles.sidebarColumn}>
              {rightSections.map((s) => (
                <Section key={s.id} id={s.id} title={s.title}>
                  {s.render()}
                </Section>
              ))}
            </div>
          </div>
        </div>
      </main>
    </Layout>
  );
}
