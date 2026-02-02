#if !defined(__STDC__) || __STDC__ == 0
#define const
#endif

#include <sys/types.h>

#if !defined(__STDC__) || __STDC__ == 0
#define BRADMAN_SIZE_T unsigned int
#else
#define BRADMAN_SIZE_T size_t
#endif
#include <ctype.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>

#if !defined(__STDC__) || __STDC__ == 0
extern int errno;
extern int _doprnt();
extern char *sys_errlist[];
extern int sys_nerr;
#endif

#if !defined(__STDC__) || __STDC__ == 0
#define BRADMAN_VOIDP char *
#else
#define BRADMAN_VOIDP void *
#endif

#if defined(__STDC__) || defined(__cplusplus)
#include <stdarg.h>
#define BRADMAN_HAVE_STDARG 1
#else
#include <varargs.h>
#endif

#if defined(__STDC__) || defined(__cplusplus)
#include <stdlib.h>
#define BRADMAN_HAVE_STDLIB 1
#endif

#ifndef BRADMAN_HAVE_STDLIB
BRADMAN_VOIDP malloc();
BRADMAN_VOIDP realloc();
void free();
void exit();
#endif

typedef struct {
  char *company;
  char *position;
  char *dateRange;
  char *location;
  char **highlights;
  BRADMAN_SIZE_T highlights_len;
  BRADMAN_SIZE_T highlights_cap;
} WorkEntry;

typedef struct {
  char *group;
  char **keywords;
  BRADMAN_SIZE_T keywords_len;
  BRADMAN_SIZE_T keywords_cap;
} SkillGroup;

typedef struct {
  char *schemaVersion;
  char *buildDate;
  char *name;
  char *label;
  char *email;
  char *url;
  char *linkedin;
  char *summary;
  WorkEntry *work;
  BRADMAN_SIZE_T work_len;
  BRADMAN_SIZE_T work_cap;
  SkillGroup *skills;
  BRADMAN_SIZE_T skills_len;
  BRADMAN_SIZE_T skills_cap;
} Resume;

typedef struct {
  char *name;
  char *label;
  char *email;
  char *github;
  char *linkedin;
} ContactInfo;

#ifdef BRADMAN_HAVE_STDARG
static void die(const char *fmt, ...) {
  va_list ap;
  va_start(ap, fmt);
  vfprintf(stderr, fmt, ap);
  va_end(ap);
  fputc('\n', stderr);
  exit(2);
}
#else
static void die(va_alist)
    va_dcl {
  va_list ap;
  const char *fmt;
  va_start(ap);
  fmt = va_arg(ap, const char *);
  vfprintf(stderr, fmt, ap);
  va_end(ap);
  fputc('\n', stderr);
  exit(2);
}
#endif

#if !defined(__STDC__) || __STDC__ == 0
static int vfprintf(stream, fmt, ap)
    FILE *stream;
    const char *fmt;
    va_list ap;
{
  return _doprnt(fmt, ap, stream);
}

static char *strerror(err)
    int err;
{
  if (err >= 0 && err < sys_nerr) return sys_errlist[err];
  return "Unknown error";
}
#endif

static BRADMAN_VOIDP xrealloc(p, n)
    BRADMAN_VOIDP p;
    BRADMAN_SIZE_T n;
{
  BRADMAN_VOIDP q;
  q = realloc(p, n);
  if (!q && n) die("out of memory");
  return q;
}

static char *xstrdup(s)
    const char *s;
{
  BRADMAN_SIZE_T n;
  char *p;
  n = strlen(s);
  p = (char *)malloc(n + 1);
  if (!p) die("out of memory");
  memcpy(p, s, n + 1);
  return p;
}

static void rstrip(s)
    char *s;
{
  BRADMAN_SIZE_T n;
  n = strlen(s);
  while (n > 0 && (s[n - 1] == '\n' || s[n - 1] == '\r' || isspace((unsigned char)s[n - 1])))
    s[--n] = '\0';
}

static int count_indent(s)
    const char *s;
{
  int n;
  n = 0;
  while (*s == ' ') {
    n++;
    s++;
  }
  return n;
}

static const char *skip_ws(s)
    const char *s;
{
  while (*s && isspace((unsigned char)*s)) s++;
  return s;
}

static int starts_with(s, pfx)
    const char *s;
    const char *pfx;
{
  return strncmp(s, pfx, strlen(pfx)) == 0;
}

static char *parse_quoted(s)
    const char *s;
{
  BRADMAN_SIZE_T cap;
  BRADMAN_SIZE_T len;
  char *out;
  unsigned char c;
  unsigned char e;
  /* Expect a double-quoted YAML scalar with minimal escape support. */
  if (*s != '"') die("expected double-quoted string");
  s++;
  cap = 64;
  len = 0;
  out = (char *)malloc(cap);
  if (!out) die("out of memory");

  while (*s && *s != '"') {
    c = (unsigned char)*s++;
    if (c == '\\') {
      e = (unsigned char)*s++;
      if (!e) die("unterminated escape");
      if (e == 'n')
        c = '\n';
      else if (e == '"' || e == '\\')
        c = e;
      else
        die("unsupported escape: \\%c", e);
    }
    if (len + 2 > cap) {
      cap *= 2;
      out = (char *)xrealloc(out, cap);
    }
    out[len++] = (char)c;
  }
  if (*s != '"') die("unterminated quoted string");
  out[len] = '\0';
  return out;
}

static int parse_key_value(line, key_out, val_out)
    const char *line;
    char **key_out;
    char **val_out;
{
  const char *colon;
  BRADMAN_SIZE_T klen;
  char *key;
  const char *rest;
  char *val;
  /* Parses: key: "value"  OR  key:   (no value) */
  colon = strchr(line, ':');
  if (!colon) return 0;

  klen = (BRADMAN_SIZE_T)(colon - line);
  while (klen > 0 && isspace((unsigned char)line[klen - 1])) klen--;
  if (klen == 0) return 0;

  key = (char *)malloc(klen + 1);
  if (!key) die("out of memory");
  memcpy(key, line, klen);
  key[klen] = '\0';

  rest = skip_ws(colon + 1);
  if (*rest == '\0') {
    *key_out = key;
    *val_out = NULL;
    return 1;
  }
  if (*rest != '"') die("expected quoted scalar for key '%s'", key);
  val = parse_quoted(rest);
  *key_out = key;
  *val_out = val;
  return 1;
}

static void push_string(items, len, cap, s)
    char ***items;
    BRADMAN_SIZE_T *len;
    BRADMAN_SIZE_T *cap;
    char *s;
{
  if (*len + 1 > *cap) {
    *cap = (*cap == 0) ? 4 : (*cap * 2);
    *items = (char **)xrealloc(*items, (*cap) * sizeof((*items)[0]));
  }
  (*items)[(*len)++] = s;
}

static WorkEntry *push_work(r)
    Resume *r;
{
  WorkEntry *e;
  if (r->work_len + 1 > r->work_cap) {
    r->work_cap = (r->work_cap == 0) ? 4 : (r->work_cap * 2);
    r->work = (WorkEntry *)xrealloc(r->work, r->work_cap * sizeof(r->work[0]));
  }
  e = &r->work[r->work_len++];
  memset(e, 0, sizeof(*e));
  return e;
}

static SkillGroup *push_skill(r)
    Resume *r;
{
  SkillGroup *g;
  if (r->skills_len + 1 > r->skills_cap) {
    r->skills_cap = (r->skills_cap == 0) ? 4 : (r->skills_cap * 2);
    r->skills = (SkillGroup *)xrealloc(r->skills, r->skills_cap * sizeof(r->skills[0]));
  }
  g = &r->skills[r->skills_len++];
  memset(g, 0, sizeof(*g));
  return g;
}

static void set_field(dst, src)
    char **dst;
    char *src;
{
  if (*dst) free(*dst);
  *dst = src;
}

static void parse_resume_vax_yaml(in, r)
    FILE *in;
    Resume *r;
{
  char buf[4096];

  enum { TOP_NONE, TOP_CONTACT, TOP_WORK, TOP_SKILLS } top = TOP_NONE;
  int in_work_highlights = 0;
  int in_skill_keywords = 0;

  WorkEntry *cur_work = NULL;
  SkillGroup *cur_skill = NULL;

  while (fgets(buf, (int)sizeof(buf), in)) {
    const char *raw;
    int indent;
    const char *line;
    char *key;
    char *val;
    const char *rest;

    rstrip(buf);
    raw = buf;
    if (*raw == '\0') continue;

    indent = count_indent(raw);
    line = raw + indent;
    line = skip_ws(line);
    if (*line == '\0' || *line == '#') continue;

    if (indent <= 2) {
      in_work_highlights = 0;
      in_skill_keywords = 0;
    }

    if (indent == 0) {
      key = NULL;
      val = NULL;
      if (!parse_key_value(line, &key, &val)) die("invalid line: %s", line);

      top = TOP_NONE;
      cur_work = NULL;
      cur_skill = NULL;

      if (strcmp(key, "schemaVersion") == 0) {
        if (!val) die("schemaVersion must have a value");
        set_field(&r->schemaVersion, val);
      } else if (strcmp(key, "buildDate") == 0) {
        if (!val) die("buildDate must have a value");
        set_field(&r->buildDate, val);
      } else if (strcmp(key, "name") == 0) {
        if (!val) die("name must have a value");
        set_field(&r->name, val);
      } else if (strcmp(key, "label") == 0) {
        if (!val) die("label must have a value");
        set_field(&r->label, val);
      } else if (strcmp(key, "summary") == 0) {
        if (!val) die("summary must have a value");
        set_field(&r->summary, val);
      } else if (strcmp(key, "contact") == 0) {
        if (val) die("contact must be a mapping (no scalar value)");
        top = TOP_CONTACT;
      } else if (strcmp(key, "work") == 0) {
        if (val) die("work must be a sequence (no scalar value)");
        top = TOP_WORK;
      } else if (strcmp(key, "skills") == 0) {
        if (val) die("skills must be a sequence (no scalar value)");
        top = TOP_SKILLS;
      } else {
        /* Unknown top-level keys are ignored for forwards-compat. */
        if (val) free(val);
      }
      free(key);
      continue;
    }

    if (indent == 2 && top == TOP_CONTACT) {
      key = NULL;
      val = NULL;
      if (!parse_key_value(line, &key, &val) || !val) die("invalid contact line: %s", line);
      if (strcmp(key, "email") == 0) {
        set_field(&r->email, val);
      } else if (strcmp(key, "url") == 0) {
        set_field(&r->url, val);
      } else if (strcmp(key, "linkedin") == 0) {
        set_field(&r->linkedin, val);
      } else {
        free(val);
      }
      free(key);
      continue;
    }

    if (indent == 2 && top == TOP_WORK) {
      if (!starts_with(line, "-")) die("expected list item in work: %s", line);
      rest = skip_ws(line + 1);
      if (*rest == '\0') {
        cur_work = push_work(r);
        continue;
      }
      if (*rest == '-') die("invalid work list item: %s", line);
      if (*rest != '\0') {
        cur_work = push_work(r);
        key = NULL;
        val = NULL;
        if (!parse_key_value(rest, &key, &val)) die("invalid work list item: %s", line);
        if (!val) die("work field must have scalar value: %s", key);
        if (strcmp(key, "company") == 0)
          set_field(&cur_work->company, val);
        else if (strcmp(key, "position") == 0)
          set_field(&cur_work->position, val);
        else if (strcmp(key, "dateRange") == 0)
          set_field(&cur_work->dateRange, val);
        else if (strcmp(key, "location") == 0)
          set_field(&cur_work->location, val);
        else
          free(val);
        free(key);
        continue;
      }
    }

    if (indent == 4 && top == TOP_WORK) {
      if (!cur_work) die("work item fields appear before first list item");
      key = NULL;
      val = NULL;
      if (!parse_key_value(line, &key, &val)) die("invalid work field: %s", line);
      if (strcmp(key, "highlights") == 0) {
        if (val) die("highlights must be a sequence (no scalar value)");
        in_work_highlights = 1;
      } else if (!val) {
        die("work field must have scalar value: %s", key);
      } else if (strcmp(key, "company") == 0) {
        set_field(&cur_work->company, val);
      } else if (strcmp(key, "position") == 0) {
        set_field(&cur_work->position, val);
      } else if (strcmp(key, "dateRange") == 0) {
        set_field(&cur_work->dateRange, val);
      } else if (strcmp(key, "location") == 0) {
        set_field(&cur_work->location, val);
      } else {
        free(val);
      }
      free(key);
      continue;
    }

    if (indent == 6 && top == TOP_WORK && in_work_highlights) {
      if (!cur_work) die("highlight appears before work item");
      if (!starts_with(line, "-")) die("expected highlight list item: %s", line);
      rest = skip_ws(line + 1);
      if (*rest != '"') die("expected quoted highlight string");
      val = parse_quoted(rest);
      push_string(&cur_work->highlights, &cur_work->highlights_len, &cur_work->highlights_cap, val);
      continue;
    }

    if (indent == 2 && top == TOP_SKILLS) {
      if (!starts_with(line, "-")) die("expected list item in skills: %s", line);
      rest = skip_ws(line + 1);
      cur_skill = push_skill(r);
      if (*rest == '\0') continue;

      key = NULL;
      val = NULL;
      if (!parse_key_value(rest, &key, &val) || !val) die("invalid skills list item: %s", line);
      if (strcmp(key, "group") == 0)
        set_field(&cur_skill->group, val);
      else
        free(val);
      free(key);
      continue;
    }

    if (indent == 4 && top == TOP_SKILLS) {
      if (!cur_skill) die("skill fields appear before first list item");
      key = NULL;
      val = NULL;
      if (!parse_key_value(line, &key, &val)) die("invalid skill field: %s", line);
      if (strcmp(key, "keywords") == 0) {
        if (val) die("keywords must be a sequence (no scalar value)");
        in_skill_keywords = 1;
      } else if (!val) {
        die("skill field must have scalar value: %s", key);
      } else if (strcmp(key, "group") == 0) {
        set_field(&cur_skill->group, val);
      } else {
        free(val);
      }
      free(key);
      continue;
    }

    if (indent == 6 && top == TOP_SKILLS && in_skill_keywords) {
      if (!cur_skill) die("keyword appears before skill item");
      if (!starts_with(line, "-")) die("expected keyword list item: %s", line);
      rest = skip_ws(line + 1);
      if (*rest != '"') die("expected quoted keyword string");
      val = parse_quoted(rest);
      push_string(&cur_skill->keywords, &cur_skill->keywords_len, &cur_skill->keywords_cap, val);
      continue;
    }

    /* Unknown/extra fields are ignored to keep the parser tolerant. */
  }
}

static char *html_escape(s)
    const char *s;
{
  BRADMAN_SIZE_T cap;
  BRADMAN_SIZE_T len;
  char *out;
  unsigned char c;
  cap = strlen(s) * 6 + 16;
  len = 0;
  out = (char *)malloc(cap);
  if (!out) die("out of memory");

  for (; *s; s++) {
    c = (unsigned char)*s;
    if (c == '<') {
      if (len + 5 > cap) {
        cap *= 2;
        out = (char *)xrealloc(out, cap);
      }
      out[len++] = '&';
      out[len++] = 'l';
      out[len++] = 't';
      out[len++] = ';';
    } else if (c == '>') {
      if (len + 5 > cap) {
        cap *= 2;
        out = (char *)xrealloc(out, cap);
      }
      out[len++] = '&';
      out[len++] = 'g';
      out[len++] = 't';
      out[len++] = ';';
    } else if (c == '&') {
      if (len + 6 > cap) {
        cap *= 2;
        out = (char *)xrealloc(out, cap);
      }
      out[len++] = '&';
      out[len++] = 'a';
      out[len++] = 'm';
      out[len++] = 'p';
      out[len++] = ';';
    } else if (c == '"') {
      if (len + 7 > cap) {
        cap *= 2;
        out = (char *)xrealloc(out, cap);
      }
      out[len++] = '&';
      out[len++] = 'q';
      out[len++] = 'u';
      out[len++] = 'o';
      out[len++] = 't';
      out[len++] = ';';
    } else {
      if (len + 2 > cap) {
        cap *= 2;
        out = (char *)xrealloc(out, cap);
      }
      out[len++] = (char)c;
    }
  }
  out[len] = '\0';
  return out;
}

static void parse_contact_json(in, contact)
    FILE *in;
    ContactInfo *contact;
{
  char buf[4096];
  char *line;
  const char *key_start;
  const char *colon;
  const char *val_start;
  const char *val_end;
  BRADMAN_SIZE_T key_len;
  char *key;
  char *val;

  /* Simple JSON parser for the contact.json format:
   * { "name": "...", "label": "...", "email": "...", "github": "...", "linkedin": "..." }
   * We expect one key-value pair per line with proper JSON string quoting. */

  while (fgets(buf, (int)sizeof(buf), in)) {
    rstrip(buf);
    line = buf;
    line = (char *)skip_ws(line);
    if (*line == '{' || *line == '}' || *line == '\0') continue;

    /* Find the key (expect: "key": "value"  or  "key": "value",) */
    if (*line != '"') continue;
    key_start = line + 1;
    line++;
    while (*line && *line != '"') line++;
    if (*line != '"') die("malformed JSON: unterminated key string");
    key_len = (BRADMAN_SIZE_T)(line - key_start);
    key = (char *)malloc(key_len + 1);
    if (!key) die("out of memory");
    memcpy(key, key_start, key_len);
    key[key_len] = '\0';
    line++;

    colon = strchr(line, ':');
    if (!colon) {
      free(key);
      continue;
    }
    line = (char *)skip_ws(colon + 1);
    if (*line != '"') {
      free(key);
      continue;
    }

    val_start = line + 1;
    line++;
    while (*line && *line != '"') {
      if (*line == '\\') {
        line++;
        if (*line) line++;
      } else {
        line++;
      }
    }
    if (*line != '"') die("malformed JSON: unterminated value string");
    val_end = line;

    /* Extract value (simple copy, no escape processing for now) */
    val = (char *)malloc((BRADMAN_SIZE_T)(val_end - val_start) + 1);
    if (!val) die("out of memory");
    memcpy(val, val_start, (BRADMAN_SIZE_T)(val_end - val_start));
    val[(BRADMAN_SIZE_T)(val_end - val_start)] = '\0';

    if (strcmp(key, "name") == 0) {
      set_field(&contact->name, val);
    } else if (strcmp(key, "label") == 0) {
      set_field(&contact->label, val);
    } else if (strcmp(key, "email") == 0) {
      set_field(&contact->email, val);
    } else if (strcmp(key, "github") == 0) {
      set_field(&contact->github, val);
    } else if (strcmp(key, "linkedin") == 0) {
      set_field(&contact->linkedin, val);
    } else {
      free(val);
    }
    free(key);
  }
}

static void emit_html_fragment(out, contact)
    FILE *out;
    const ContactInfo *contact;
{
  char *name_esc;
  char *label_esc;
  char *email_esc;
  char *github_esc;
  char *linkedin_esc;

  /* Generate semantic HTML fragment for the contact section */
  fputs("<header>\n", out);

  if (contact->name && contact->name[0]) {
    name_esc = html_escape(contact->name);
    fprintf(out, "  <h1>%s</h1>\n", name_esc);
    free(name_esc);
  }

  if (contact->label && contact->label[0]) {
    label_esc = html_escape(contact->label);
    fprintf(out, "  <p class=\"subtitle\">%s</p>\n", label_esc);
    free(label_esc);
  }

  if (contact->email && contact->email[0]) {
    email_esc = html_escape(contact->email);
    fprintf(out, "  <p class=\"contact-email\">%s</p>\n", email_esc);
    free(email_esc);
  }

  fputs("  <nav>\n", out);
  if (contact->linkedin && contact->linkedin[0]) {
    linkedin_esc = html_escape(contact->linkedin);
    fprintf(out, "    <a class=\"pill\" href=\"%s\" rel=\"me noopener noreferrer\">LinkedIn</a>\n", linkedin_esc);
    free(linkedin_esc);
  }
  if (contact->github && contact->github[0]) {
    github_esc = html_escape(contact->github);
    fprintf(out, "    <a class=\"pill\" href=\"%s\" rel=\"me noopener noreferrer\">GitHub</a>\n", github_esc);
    free(github_esc);
  }
  fputs("  </nav>\n", out);
  fputs("</header>\n", out);
}

static void free_contact(c)
    ContactInfo *c;
{
  free(c->name);
  free(c->label);
  free(c->email);
  free(c->github);
  free(c->linkedin);
}

static char *roff_escape_line(s, for_name_synopsis)
    const char *s;
    int for_name_synopsis;
{
  BRADMAN_SIZE_T cap;
  BRADMAN_SIZE_T len;
  char *out;
  char c;
  cap = strlen(s) * 2 + 32;
  len = 0;
  out = (char *)malloc(cap);
  if (!out) die("out of memory");

  if (s[0] == '.' || s[0] == '\'') {
    out[len++] = '\\';
    out[len++] = '&';
  }

  for (; *s; s++) {
    c = *s;
    if (c == '\\') {
      out[len++] = '\\';
      out[len++] = '\\';
    } else if (for_name_synopsis && c == '-') {
      out[len++] = '\\';
      out[len++] = '-';
    } else {
      out[len++] = c;
    }
    if (len + 4 > cap) {
      cap *= 2;
      out = (char *)xrealloc(out, cap);
    }
  }
  out[len] = '\0';
  return out;
}

static void emit_roff(out, r)
    FILE *out;
    const Resume *r;
{
  const char *date;
  char *label;
  char *summary;
  char *email;
  char *url;
  char *li;
  BRADMAN_SIZE_T i;
  BRADMAN_SIZE_T j;
  const WorkEntry *w;
  char *company;
  char *position;
  char *dateRange;
  char *loc;
  char *hl;
  const SkillGroup *g;
  char *group;
  char *kw;
  char *name;

  date = (r->buildDate && r->buildDate[0]) ? r->buildDate : "";
  fprintf(out, ".TH BRAD 1 \"%s\" \"brfid.github.io\" \"\"\n", date);

  fputs(".SH NAME\n", out);
  label = roff_escape_line(r->label ? r->label : "", 0);
  fprintf(out, "brad \\\\- %s\n", label);
  free(label);

  if (r->summary && r->summary[0]) {
    fputs(".SH DESCRIPTION\n", out);
    summary = roff_escape_line(r->summary, 0);
    fprintf(out, "%s\n", summary);
    free(summary);
  }

  if ((r->email && r->email[0]) || (r->url && r->url[0]) || (r->linkedin && r->linkedin[0])) {
    fputs(".SH CONTACT\n", out);
    if (r->email && r->email[0]) {
      email = roff_escape_line(r->email, 0);
      fprintf(out, "Email: %s\n.br\n", email);
      free(email);
    }
    if (r->url && r->url[0]) {
      url = roff_escape_line(r->url, 0);
      fprintf(out, "Web: %s\n.br\n", url);
      free(url);
    }
    if (r->linkedin && r->linkedin[0]) {
      li = roff_escape_line(r->linkedin, 0);
      fprintf(out, "LinkedIn: %s\n", li);
      free(li);
    }
  }

  if (r->work_len) {
    fputs(".SH EXPERIENCE\n", out);
    for (i = 0; i < r->work_len; i++) {
      w = &r->work[i];
      if (!w->company && !w->position) continue;

      company = roff_escape_line(w->company ? w->company : "", 0);
      position = roff_escape_line(w->position ? w->position : "", 0);
      dateRange = roff_escape_line(w->dateRange ? w->dateRange : "", 0);
      fputs(".TP\n", out);
      if (w->position && w->position[0]) {
        fprintf(out, ".B %s\n%s", company, position);
      } else {
        fprintf(out, ".B %s\n", company);
      }
      if (w->dateRange && w->dateRange[0]) fprintf(out, " (%s)", dateRange);
      fputc('\n', out);
      free(company);
      free(position);
      free(dateRange);

      if (w->location && w->location[0]) {
        loc = roff_escape_line(w->location, 0);
        fprintf(out, ".I %s\n", loc);
        free(loc);
      }

      for (j = 0; j < w->highlights_len; j++) {
        hl = roff_escape_line(w->highlights[j], 0);
        fprintf(out, ".IP \\\\(bu 2\n%s\n", hl);
        free(hl);
      }
    }
  }

  if (r->skills_len) {
    fputs(".SH SKILLS\n", out);
    for (i = 0; i < r->skills_len; i++) {
      g = &r->skills[i];
      if (!g->group || !g->group[0]) continue;
      group = roff_escape_line(g->group, 0);
      fprintf(out, ".SS %s\n", group);
      free(group);
      for (j = 0; j < g->keywords_len; j++) {
        kw = roff_escape_line(g->keywords[j], 0);
        fputs(kw, out);
        free(kw);
        if (j + 1 < g->keywords_len) fputs(", ", out);
      }
      fputc('\n', out);
    }
  }

  if (r->name && r->name[0]) {
    fputs(".SH AUTHOR\n", out);
    name = roff_escape_line(r->name, 0);
    fprintf(out, "%s\n", name);
    free(name);
  }
}

static void free_resume(r)
    Resume *r;
{
  BRADMAN_SIZE_T i;
  BRADMAN_SIZE_T j;
  WorkEntry *w;
  SkillGroup *g;
  free(r->schemaVersion);
  free(r->buildDate);
  free(r->name);
  free(r->label);
  free(r->email);
  free(r->url);
  free(r->linkedin);
  free(r->summary);

  for (i = 0; i < r->work_len; i++) {
    w = &r->work[i];
    free(w->company);
    free(w->position);
    free(w->dateRange);
    free(w->location);
    for (j = 0; j < w->highlights_len; j++) free(w->highlights[j]);
    free(w->highlights);
  }
  free(r->work);

  for (i = 0; i < r->skills_len; i++) {
    g = &r->skills[i];
    free(g->group);
    for (j = 0; j < g->keywords_len; j++) free(g->keywords[j]);
    free(g->keywords);
  }
  free(r->skills);
}

static void usage(argv0)
    const char *argv0;
{
  fprintf(stderr, "usage: %s -i INPUT [-o OUTPUT] [-mode roff|html]\n", argv0);
  fprintf(stderr, "  roff mode (default): -i resume.vax.yaml -o brad.1\n");
  fprintf(stderr, "  html mode: -i contact.json -o contact.html\n");
  exit(2);
}

int main(argc, argv)
    int argc;
    char **argv;
{
  int i;
  const char *in_path;
  const char *out_path;
  const char *mode;
  FILE *in;
  FILE *out;
  Resume r;
  ContactInfo c;

  in_path = NULL;
  out_path = NULL;
  mode = "roff";

  for (i = 1; i < argc; i++) {
    if (strcmp(argv[i], "-i") == 0) {
      if (++i >= argc) usage(argv[0]);
      in_path = argv[i];
    } else if (strcmp(argv[i], "-o") == 0) {
      if (++i >= argc) usage(argv[0]);
      out_path = argv[i];
    } else if (strcmp(argv[i], "-mode") == 0) {
      if (++i >= argc) usage(argv[0]);
      mode = argv[i];
    } else {
      usage(argv[0]);
    }
  }

  if (!in_path) usage(argv[0]);

  if (strcmp(mode, "roff") != 0 && strcmp(mode, "html") != 0) {
    die("invalid mode: %s (expected 'roff' or 'html')", mode);
  }

  in = fopen(in_path, "r");
  if (!in) die("open %s: %s", in_path, strerror(errno));

  out = stdout;
  if (out_path && strcmp(out_path, "-") != 0) {
    out = fopen(out_path, "w");
    if (!out) die("open %s: %s", out_path, strerror(errno));
  }

  if (strcmp(mode, "html") == 0) {
    memset(&c, 0, sizeof(c));
    parse_contact_json(in, &c);
    fclose(in);
    emit_html_fragment(out, &c);
    if (out != stdout) fclose(out);
    free_contact(&c);
  } else {
    memset(&r, 0, sizeof(r));
    parse_resume_vax_yaml(in, &r);
    fclose(in);
    if (!r.schemaVersion || strcmp(r.schemaVersion, "v1") != 0) {
      die("unsupported or missing schemaVersion (expected \"v1\")");
    }
    if (!r.label) die("missing required field: label");
    emit_roff(out, &r);
    if (out != stdout) fclose(out);
    free_resume(&r);
  }

  return 0;
}
