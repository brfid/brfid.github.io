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

/* Convert the fixed host-generated bio mapping to troff on 4.3BSD. */

typedef struct {
  char *schemaVersion;
  char *buildDate;
  char *bioName;
  char *bioHeadline;
  char *bioProfile;
} Bio;

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

static char *parse_unquoted(s)
    const char *s;
{
  BRADMAN_SIZE_T cap;
  BRADMAN_SIZE_T len;
  char *out;
  const char *end;
  /* Parse an unquoted YAML scalar through the next indicator or line end. */
  end = s;
  while (*end) {
    unsigned char c = (unsigned char)*end;
    /* Stop at YAML indicators (except : must be followed by space/newline) */
    if (c == '\0' || c == '\n') break;
    if (c == '#' || c == '[' || c == ']' || c == '{' || c == '}' || c == ',') break;
    /* Colon is only special if followed by space or end */
    if (c == ':' && (end[1] == ' ' || end[1] == '\t' || end[1] == '\n' || end[1] == '\0')) break;
    end++;
  }

  /* Trim trailing whitespace */
  while (end > s && isspace((unsigned char)*(end - 1))) {
    end--;
  }

  len = (BRADMAN_SIZE_T)(end - s);
  if (len == 0) die("empty unquoted string");

  out = (char *)malloc(len + 1);
  if (!out) die("out of memory");
  memcpy(out, s, len);
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
  /* Accept key: "value", key: value, or an empty value. */
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
  /* Auto-detect quoted vs unquoted strings */
  if (*rest == '"') {
    val = parse_quoted(rest);
  } else {
    val = parse_unquoted(rest);
  }
  *key_out = key;
  *val_out = val;
  return 1;
}

static void set_field(dst, src)
    char **dst;
    char *src;
{
  if (*dst) free(*dst);
  *dst = src;
}

static void parse_bio_yaml(in, b)
    FILE *in;
    Bio *b;
{
  char buf[4096];

  while (fgets(buf, (int)sizeof(buf), in)) {
    const char *raw;
    int indent;
    const char *line;
    char *key;
    char *val;

    rstrip(buf);
    raw = buf;
    if (*raw == '\0') continue;

    indent = count_indent(raw);
    line = raw + indent;
    line = skip_ws(line);
    if (*line == '\0' || *line == '#') continue;

    /* The bio YAML is flat; only top-level scalar keys are meaningful. */
    if (indent != 0) continue;

    key = NULL;
    val = NULL;
    if (!parse_key_value(line, &key, &val)) die("invalid line: %s", line);

    if (strcmp(key, "schemaVersion") == 0) {
      if (!val) die("schemaVersion must have a value");
      set_field(&b->schemaVersion, val);
    } else if (strcmp(key, "buildDate") == 0) {
      if (!val) die("buildDate must have a value");
      set_field(&b->buildDate, val);
    } else if (strcmp(key, "bioName") == 0) {
      if (!val) die("bioName must have a value");
      set_field(&b->bioName, val);
    } else if (strcmp(key, "bioHeadline") == 0) {
      if (!val) die("bioHeadline must have a value");
      set_field(&b->bioHeadline, val);
    } else if (strcmp(key, "bioProfile") == 0) {
      if (!val) die("bioProfile must have a value");
      set_field(&b->bioProfile, val);
    } else {
      /* Host serialization rejects unknown keys; ignore them defensively here. */
      if (val) free(val);
    }
    free(key);
  }
}

static char *roff_escape_line(s)
    const char *s;
{
  BRADMAN_SIZE_T cap;
  BRADMAN_SIZE_T len;
  char *out;
  char c;
  cap = strlen(s) * 2 + 32;
  len = 0;
  out = (char *)malloc(cap);
  if (!out) die("out of memory");

  /* A leading control character (. or ') would be read as a request; guard it. */
  if (s[0] == '.' || s[0] == '\'') {
    out[len++] = '\\';
    out[len++] = '&';
  }

  for (; *s; s++) {
    c = *s;
    if (c == '\\') {
      out[len++] = '\\';
      out[len++] = '\\';
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

static void emit_bio_roff(out, b)
    FILE *out;
    const Bio *b;
{
  char *esc;

  /* Provenance comment; nroff strips it, so it never reaches the rendered bio. */
  if (b->buildDate && b->buildDate[0]) {
    fprintf(out, ".\\\" bradman bio, build %s\n", b->buildDate);
  }

  /* Use a stable 60-column measure with no default page offset or hyphenation.
   * Whole words let the host compare the render with resume.yaml basics.summary. */
  fputs(".ll 60n\n", out);
  fputs(".po 0\n", out);
  fputs(".nh\n", out);

  /* Header lines set verbatim (no fill), one per line. */
  fputs(".nf\n", out);
  if (b->bioName && b->bioName[0]) {
    esc = roff_escape_line(b->bioName);
    fprintf(out, "%s\n", esc);
    free(esc);
  }
  if (b->bioHeadline && b->bioHeadline[0]) {
    esc = roff_escape_line(b->bioHeadline);
    fprintf(out, "%s\n", esc);
    free(esc);
  }
  fputs(".fi\n", out);

  /* Fill and justify the summary. */
  fputs(".ad b\n", out);
  fputs(".sp\n", out);
  if (b->bioProfile && b->bioProfile[0]) {
    esc = roff_escape_line(b->bioProfile);
    fprintf(out, "%s\n", esc);
    free(esc);
  }
}

static void free_bio(b)
    Bio *b;
{
  free(b->schemaVersion);
  free(b->buildDate);
  free(b->bioName);
  free(b->bioHeadline);
  free(b->bioProfile);
}

static void usage(argv0)
    const char *argv0;
{
  fprintf(stderr, "usage: %s -i BIO_YAML [-o BRAD_BIO_ROFF]\n", argv0);
  exit(2);
}

int main(argc, argv)
    int argc;
    char **argv;
{
  int i;
  const char *in_path;
  const char *out_path;
  FILE *in;
  FILE *out;
  Bio b;

  in_path = NULL;
  out_path = NULL;

  for (i = 1; i < argc; i++) {
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

  in = fopen(in_path, "r");
  if (!in) die("open %s: %s", in_path, strerror(errno));

  out = stdout;
  if (out_path && strcmp(out_path, "-") != 0) {
    out = fopen(out_path, "w");
    if (!out) die("open %s: %s", out_path, strerror(errno));
  }

  memset(&b, 0, sizeof(b));
  parse_bio_yaml(in, &b);
  fclose(in);

  if (!b.schemaVersion || strcmp(b.schemaVersion, "v1") != 0) {
    die("unsupported or missing schemaVersion (expected \"v1\")");
  }
  if (!b.bioProfile || !b.bioProfile[0]) {
    die("missing required field: bioProfile");
  }

  emit_bio_roff(out, &b);
  if (out != stdout) fclose(out);
  free_bio(&b);

  return 0;
}
