#include <ctype.h>
#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
  char *company;
  char *position;
  char *dateRange;
  char *location;
  char **highlights;
  size_t highlights_len;
  size_t highlights_cap;
} WorkEntry;

typedef struct {
  char *group;
  char **keywords;
  size_t keywords_len;
  size_t keywords_cap;
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
  size_t work_len;
  size_t work_cap;
  SkillGroup *skills;
  size_t skills_len;
  size_t skills_cap;
} Resume;

static void die(const char *fmt, ...) {
  va_list ap;
  va_start(ap, fmt);
  vfprintf(stderr, fmt, ap);
  va_end(ap);
  fputc('\n', stderr);
  exit(2);
}

static void *xrealloc(void *p, size_t n) {
  void *q = realloc(p, n);
  if (!q && n) die("out of memory");
  return q;
}

static char *xstrdup(const char *s) {
  size_t n = strlen(s);
  char *p = (char *)malloc(n + 1);
  if (!p) die("out of memory");
  memcpy(p, s, n + 1);
  return p;
}

static void rstrip(char *s) {
  size_t n = strlen(s);
  while (n > 0 && (s[n - 1] == '\n' || s[n - 1] == '\r' || isspace((unsigned char)s[n - 1])))
    s[--n] = '\0';
}

static int count_indent(const char *s) {
  int n = 0;
  while (*s == ' ') {
    n++;
    s++;
  }
  return n;
}

static const char *skip_ws(const char *s) {
  while (*s && isspace((unsigned char)*s)) s++;
  return s;
}

static int starts_with(const char *s, const char *pfx) { return strncmp(s, pfx, strlen(pfx)) == 0; }

static char *parse_quoted(const char *s) {
  /* Expect a double-quoted YAML scalar with minimal escape support. */
  if (*s != '"') die("expected double-quoted string");
  s++;
  size_t cap = 64, len = 0;
  char *out = (char *)malloc(cap);
  if (!out) die("out of memory");

  while (*s && *s != '"') {
    unsigned char c = (unsigned char)*s++;
    if (c == '\\') {
      unsigned char e = (unsigned char)*s++;
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

static int parse_key_value(const char *line, char **key_out, char **val_out) {
  /* Parses: key: "value"  OR  key:   (no value) */
  const char *colon = strchr(line, ':');
  if (!colon) return 0;

  size_t klen = (size_t)(colon - line);
  while (klen > 0 && isspace((unsigned char)line[klen - 1])) klen--;
  if (klen == 0) return 0;

  char *key = (char *)malloc(klen + 1);
  if (!key) die("out of memory");
  memcpy(key, line, klen);
  key[klen] = '\0';

  const char *rest = skip_ws(colon + 1);
  if (*rest == '\0') {
    *key_out = key;
    *val_out = NULL;
    return 1;
  }
  if (*rest != '"') die("expected quoted scalar for key '%s'", key);
  char *val = parse_quoted(rest);
  *key_out = key;
  *val_out = val;
  return 1;
}

static void push_string(char ***items, size_t *len, size_t *cap, char *s) {
  if (*len + 1 > *cap) {
    *cap = (*cap == 0) ? 4 : (*cap * 2);
    *items = (char **)xrealloc(*items, (*cap) * sizeof((*items)[0]));
  }
  (*items)[(*len)++] = s;
}

static WorkEntry *push_work(Resume *r) {
  if (r->work_len + 1 > r->work_cap) {
    r->work_cap = (r->work_cap == 0) ? 4 : (r->work_cap * 2);
    r->work = (WorkEntry *)xrealloc(r->work, r->work_cap * sizeof(r->work[0]));
  }
  WorkEntry *e = &r->work[r->work_len++];
  memset(e, 0, sizeof(*e));
  return e;
}

static SkillGroup *push_skill(Resume *r) {
  if (r->skills_len + 1 > r->skills_cap) {
    r->skills_cap = (r->skills_cap == 0) ? 4 : (r->skills_cap * 2);
    r->skills = (SkillGroup *)xrealloc(r->skills, r->skills_cap * sizeof(r->skills[0]));
  }
  SkillGroup *g = &r->skills[r->skills_len++];
  memset(g, 0, sizeof(*g));
  return g;
}

static void set_field(char **dst, char *src) {
  if (*dst) free(*dst);
  *dst = src;
}

static void parse_resume_vax_yaml(FILE *in, Resume *r) {
  char buf[4096];

  enum { TOP_NONE, TOP_CONTACT, TOP_WORK, TOP_SKILLS } top = TOP_NONE;
  int in_work_highlights = 0;
  int in_skill_keywords = 0;

  WorkEntry *cur_work = NULL;
  SkillGroup *cur_skill = NULL;

  while (fgets(buf, (int)sizeof(buf), in)) {
    rstrip(buf);
    const char *raw = buf;
    if (*raw == '\0') continue;

    int indent = count_indent(raw);
    const char *line = raw + indent;
    line = skip_ws(line);
    if (*line == '\0' || *line == '#') continue;

    if (indent <= 2) {
      in_work_highlights = 0;
      in_skill_keywords = 0;
    }

    if (indent == 0) {
      char *key = NULL, *val = NULL;
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
      char *key = NULL, *val = NULL;
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
      const char *rest = skip_ws(line + 1);
      if (*rest == '\0') {
        cur_work = push_work(r);
        continue;
      }
      if (*rest == '-') die("invalid work list item: %s", line);
      if (*rest != '\0') {
        cur_work = push_work(r);
        char *key = NULL, *val = NULL;
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
      char *key = NULL, *val = NULL;
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
      const char *rest = skip_ws(line + 1);
      if (*rest != '"') die("expected quoted highlight string");
      char *val = parse_quoted(rest);
      push_string(&cur_work->highlights, &cur_work->highlights_len, &cur_work->highlights_cap, val);
      continue;
    }

    if (indent == 2 && top == TOP_SKILLS) {
      if (!starts_with(line, "-")) die("expected list item in skills: %s", line);
      const char *rest = skip_ws(line + 1);
      cur_skill = push_skill(r);
      if (*rest == '\0') continue;

      char *key = NULL, *val = NULL;
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
      char *key = NULL, *val = NULL;
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
      const char *rest = skip_ws(line + 1);
      if (*rest != '"') die("expected quoted keyword string");
      char *val = parse_quoted(rest);
      push_string(&cur_skill->keywords, &cur_skill->keywords_len, &cur_skill->keywords_cap, val);
      continue;
    }

    /* Unknown/extra fields are ignored to keep the parser tolerant. */
  }
}

static char *roff_escape_line(const char *s, int for_name_synopsis) {
  size_t cap = strlen(s) * 2 + 32;
  size_t len = 0;
  char *out = (char *)malloc(cap);
  if (!out) die("out of memory");

  if (s[0] == '.' || s[0] == '\'') {
    out[len++] = '\\';
    out[len++] = '&';
  }

  for (; *s; s++) {
    char c = *s;
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

static void emit_roff(FILE *out, const Resume *r) {
  const char *date = (r->buildDate && r->buildDate[0]) ? r->buildDate : "";
  fprintf(out, ".TH BRAD 1 \"%s\" \"brfid.github.io\" \"\"\n", date);

  fputs(".SH NAME\n", out);
  char *label = roff_escape_line(r->label ? r->label : "", 0);
  fprintf(out, "brad \\\\- %s\n", label);
  free(label);

  if (r->summary && r->summary[0]) {
    fputs(".SH DESCRIPTION\n", out);
    char *summary = roff_escape_line(r->summary, 0);
    fprintf(out, "%s\n", summary);
    free(summary);
  }

  if ((r->email && r->email[0]) || (r->url && r->url[0]) || (r->linkedin && r->linkedin[0])) {
    fputs(".SH CONTACT\n", out);
    if (r->email && r->email[0]) {
      char *email = roff_escape_line(r->email, 0);
      fprintf(out, "Email: %s\n.br\n", email);
      free(email);
    }
    if (r->url && r->url[0]) {
      char *url = roff_escape_line(r->url, 0);
      fprintf(out, "Web: %s\n.br\n", url);
      free(url);
    }
    if (r->linkedin && r->linkedin[0]) {
      char *li = roff_escape_line(r->linkedin, 0);
      fprintf(out, "LinkedIn: %s\n", li);
      free(li);
    }
  }

  if (r->work_len) {
    fputs(".SH EXPERIENCE\n", out);
    for (size_t i = 0; i < r->work_len; i++) {
      const WorkEntry *w = &r->work[i];
      if (!w->company && !w->position) continue;

      char *company = roff_escape_line(w->company ? w->company : "", 0);
      char *position = roff_escape_line(w->position ? w->position : "", 0);
      char *dateRange = roff_escape_line(w->dateRange ? w->dateRange : "", 0);
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
        char *loc = roff_escape_line(w->location, 0);
        fprintf(out, ".I %s\n", loc);
        free(loc);
      }

      for (size_t j = 0; j < w->highlights_len; j++) {
        char *hl = roff_escape_line(w->highlights[j], 0);
        fprintf(out, ".IP \\\\(bu 2\n%s\n", hl);
        free(hl);
      }
    }
  }

  if (r->skills_len) {
    fputs(".SH SKILLS\n", out);
    for (size_t i = 0; i < r->skills_len; i++) {
      const SkillGroup *g = &r->skills[i];
      if (!g->group || !g->group[0]) continue;
      char *group = roff_escape_line(g->group, 0);
      fprintf(out, ".SS %s\n", group);
      free(group);
      for (size_t j = 0; j < g->keywords_len; j++) {
        char *kw = roff_escape_line(g->keywords[j], 0);
        fputs(kw, out);
        free(kw);
        if (j + 1 < g->keywords_len) fputs(", ", out);
      }
      fputc('\n', out);
    }
  }

  if (r->name && r->name[0]) {
    fputs(".SH AUTHOR\n", out);
    char *name = roff_escape_line(r->name, 0);
    fprintf(out, "%s\n", name);
    free(name);
  }
}

static void free_resume(Resume *r) {
  free(r->schemaVersion);
  free(r->buildDate);
  free(r->name);
  free(r->label);
  free(r->email);
  free(r->url);
  free(r->linkedin);
  free(r->summary);

  for (size_t i = 0; i < r->work_len; i++) {
    WorkEntry *w = &r->work[i];
    free(w->company);
    free(w->position);
    free(w->dateRange);
    free(w->location);
    for (size_t j = 0; j < w->highlights_len; j++) free(w->highlights[j]);
    free(w->highlights);
  }
  free(r->work);

  for (size_t i = 0; i < r->skills_len; i++) {
    SkillGroup *g = &r->skills[i];
    free(g->group);
    for (size_t j = 0; j < g->keywords_len; j++) free(g->keywords[j]);
    free(g->keywords);
  }
  free(r->skills);
}

static void usage(const char *argv0) {
  fprintf(stderr, "usage: %s -i resume.vax.yaml [-o brad.1]\n", argv0);
  exit(2);
}

int main(int argc, char **argv) {
  const char *in_path = NULL;
  const char *out_path = NULL;

  for (int i = 1; i < argc; i++) {
    if (strcmp(argv[i], "-i") == 0) {
      if (++i >= argc) usage(argv[0]);
      in_path = argv[i];
    } else if (strcmp(argv[i], "-o") == 0) {
      if (++i >= argc) usage(argv[0]);
      out_path = argv[i];
    } else {
      usage(argv[0]);
    }
  }

  if (!in_path) usage(argv[0]);

  FILE *in = fopen(in_path, "r");
  if (!in) die("open %s: %s", in_path, strerror(errno));

  FILE *out = stdout;
  if (out_path && strcmp(out_path, "-") != 0) {
    out = fopen(out_path, "w");
    if (!out) die("open %s: %s", out_path, strerror(errno));
  }

  Resume r;
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
  return 0;
}

