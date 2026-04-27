do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'profiles_email_length_check'
  ) then
    alter table public.profiles
      add constraint profiles_email_length_check check (email is null or char_length(email) <= 320);
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'profiles_full_name_length_check'
  ) then
    alter table public.profiles
      add constraint profiles_full_name_length_check check (full_name is null or char_length(full_name) <= 200);
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'profiles_organization_name_length_check'
  ) then
    alter table public.profiles
      add constraint profiles_organization_name_length_check check (organization_name is null or char_length(organization_name) <= 200);
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'profiles_title_length_check'
  ) then
    alter table public.profiles
      add constraint profiles_title_length_check check (title is null or char_length(title) <= 160);
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'profiles_avatar_url_length_check'
  ) then
    alter table public.profiles
      add constraint profiles_avatar_url_length_check check (avatar_url is null or char_length(avatar_url) <= 2048);
  end if;
end;
$$;

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'company_profiles_legal_entity_name_length_check'
  ) then
    alter table public.company_profiles
      add constraint company_profiles_legal_entity_name_length_check check (char_length(legal_entity_name) <= 240);
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'company_profiles_doing_business_as_length_check'
  ) then
    alter table public.company_profiles
      add constraint company_profiles_doing_business_as_length_check check (doing_business_as is null or char_length(doing_business_as) <= 240);
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'company_profiles_business_number_length_check'
  ) then
    alter table public.company_profiles
      add constraint company_profiles_business_number_length_check check (business_number is null or char_length(business_number) <= 40);
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'company_profiles_website_format_check'
  ) then
    alter table public.company_profiles
      add constraint company_profiles_website_format_check check (
        website is null
        or (
          char_length(website) <= 2048
          and website ~* '^https?://'
        )
      );
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'company_profiles_city_length_check'
  ) then
    alter table public.company_profiles
      add constraint company_profiles_city_length_check check (city is null or char_length(city) <= 120);
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'company_profiles_industry_length_check'
  ) then
    alter table public.company_profiles
      add constraint company_profiles_industry_length_check check (industry is null or char_length(industry) <= 100);
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'company_profiles_sub_sector_length_check'
  ) then
    alter table public.company_profiles
      add constraint company_profiles_sub_sector_length_check check (sub_sector is null or char_length(sub_sector) <= 100);
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'company_profiles_keywords_length_check'
  ) then
    alter table public.company_profiles
      add constraint company_profiles_keywords_length_check check (keywords is null or char_length(keywords) <= 2000);
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'company_profiles_funding_need_upper_check'
  ) then
    alter table public.company_profiles
      add constraint company_profiles_funding_need_upper_check check (
        funding_need is null or funding_need <= 100000000000
      );
  end if;
end;
$$;
