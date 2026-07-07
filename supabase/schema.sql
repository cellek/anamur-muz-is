-- AnamurMuzİş — Supabase şeması
-- Kurulum: Supabase Dashboard -> SQL Editor -> bu dosyanın tamamını yapıştırıp Run.

-- ===== İş ilanları (işveren) =====
create table public.jobs (
  id             uuid primary key default gen_random_uuid(),
  title          text not null check (char_length(title) between 1 and 120),
  employer       text not null check (char_length(employer) between 1 and 80),
  location       text not null check (char_length(location) between 1 and 80),
  work_type      text not null check (char_length(work_type) between 1 and 40),
  wage           text not null check (char_length(wage) between 1 and 80),
  workers_needed integer not null default 1 check (workers_needed between 1 and 999),
  start_date     date,
  duration       text check (char_length(duration) <= 60),
  phone          text not null check (char_length(phone) between 5 and 30),
  description    text check (char_length(description) <= 600),
  created_at     timestamptz not null default now()
);

-- ===== İş arayanlar (işçi müsaitlik) =====
create table public.workers (
  id             uuid primary key default gen_random_uuid(),
  name           text not null check (char_length(name) between 1 and 80),
  work_types     text[] not null check (array_length(work_types, 1) between 1 and 6),
  experience     text check (char_length(experience) <= 200),
  available_from date,
  expected_wage  text check (char_length(expected_wage) <= 80),
  location       text not null check (char_length(location) between 1 and 80),
  phone          text not null check (char_length(phone) between 5 and 30),
  note           text check (char_length(note) <= 600),
  created_at     timestamptz not null default now()
);

create index jobs_created_at_idx on public.jobs (created_at desc);
create index workers_created_at_idx on public.workers (created_at desc);

-- ===== Güvenlik (RLS) =====
-- Herkes okuyabilir ve yeni ilan ekleyebilir; ancak kimse mevcut ilanları
-- değiştiremez veya silemez (update/delete politikası yok).
alter table public.jobs enable row level security;
alter table public.workers enable row level security;

create policy "jobs: herkes okuyabilir"    on public.jobs    for select using (true);
create policy "jobs: herkes ekleyebilir"   on public.jobs    for insert with check (true);
create policy "workers: herkes okuyabilir"  on public.workers for select using (true);
create policy "workers: herkes ekleyebilir" on public.workers for insert with check (true);

-- ===== Örnek veriler =====
insert into public.jobs (title, employer, location, work_type, wage, workers_needed, start_date, duration, phone, description) values
  ('Muz hasadı için 5 işçi aranıyor', 'Yılmaz Tarım', 'Ören Mahallesi', 'Hasat', 'Günlük 900 TL + yemek', 5, '2026-07-10', '2 hafta', '0532 000 00 01', 'Sera muz hasadı. Deneyimli işçiler tercih edilir. Servis mevcuttur.'),
  ('Paketleme tesisine eleman alınacak', 'Anamur Muz Paketleme', 'Bahçelievler', 'Paketleme', 'Aylık 26.000 TL, sigortalı', 3, '2026-07-15', 'Sürekli', '0532 000 00 02', 'Muz paketleme ve etiketleme. Kadın-erkek eleman alınacaktır.');

insert into public.workers (name, work_types, experience, available_from, expected_wage, location, phone, note) values
  ('Mehmet K.', array['Hasat', 'Bakım / İlaçlama'], '8 yıl sera muz deneyimi', '2026-07-07', 'Günlük 850 TL', 'Anamur Merkez', '0532 000 00 03', 'Kendi ulaşımım var, Ören ve Kaledran tarafına gidebilirim.');
