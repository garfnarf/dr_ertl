import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const aktuelles = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/aktuelles' }),
  schema: z.object({
    titel: z.string(),
    kicker: z.string(),
    reihenfolge: z.number(),
    sichtbar: z.boolean().default(true),
    listenIcon: z.enum(['chevron', 'warnung']).default('chevron'),
    rezeptformular: z.boolean().default(false),
    button: z.object({ text: z.string(), url: z.string() }).optional(),
  }),
});

const leistungen = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/leistungen' }),
  schema: z.object({
    titel: z.string(),
    untertitel: z.string(),
    icon: z.string(),
    bild: z.string(),
    reihenfolge: z.number(),
  }),
});

const aerzte = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/aerzte' }),
  schema: z.object({
    name: z.string(),
    beschreibung: z.string().optional(),
    untertitel: z.string(),
    foto: z.string(),
    fotoQuadrat: z.string(),
    reihenfolge: z.number(),
    zitat: z.string(),
    stationen: z.array(z.object({ zeitraum: z.string(), text: z.string() })),
  }),
});

const team = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/team' }),
  schema: z.object({
    name: z.string(),
    rolle: z.string(),
    foto: z.string(),
    reihenfolge: z.number(),
  }),
});

const seiten = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/seiten' }),
  schema: z.object({
    titel: z.string(),
  }),
});

export const collections = { aktuelles, leistungen, aerzte, team, seiten };
