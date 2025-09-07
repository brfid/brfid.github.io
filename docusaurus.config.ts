import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Brad Fidler',
  tagline: 'Senior Technical Writer',
  favicon: 'img/favicon.ico',

  future: {
    v4: true,
  },

  url: 'https://brfid.github.io',
  baseUrl: '/',

  organizationName: 'brfid',
  projectName: 'brfid.github.io',

  onBrokenLinks: 'ignore',
  onBrokenMarkdownLinks: 'warn',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          editUrl:
            'https://github.com/brfid/brfid.github.io/tree/main/',
        },
        blog: {
          path: 'blog',
          routeBasePath: 'blog',
          showReadingTime: true,
          onUntruncatedBlogPosts: 'ignore',
        },
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    // Replace with your project's social card
    image: 'img/docusaurus-social-card.jpg',
    navbar: {
      title: 'My Site',
      logo: {
        alt: 'My Site Logo',
        src: 'img/logo.svg',
      },
      items: [
        { to: '/blog', label: 'Blog', position: 'left' },
        { to: '/resume', label: 'Resume', position: 'left' },
        {
          href: '/resume.pdf',
          label: 'Download Resume',
          position: 'right',
          'aria-label': 'Download Resume PDF',
          target: '_blank',
          rel: 'noopener noreferrer',
          'data-no-route': true,
        },
        {
          href: 'https://github.com/brfid/brfid.github.io/',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      copyright: `© ${new Date().getFullYear()} Bradley Fidler`,
    },
    
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
