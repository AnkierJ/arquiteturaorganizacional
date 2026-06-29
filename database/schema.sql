create table if not exists public.colaboradores (
    mat text primary key,
    nome text not null,
    cargo text default '' not null,
    supersetor text default '' not null,
    setor text default '' not null,
    subsetor text default '' not null,
    lider text default '' not null,
    posicao text default '' not null,
    observacoes text default '' not null,
    updated_at timestamptz default now() not null
);

create table if not exists public.hierarchy_setores (
    setor text primary key,
    lidermat text default '' not null,
    sort_order integer default 0 not null,
    updated_at timestamptz default now() not null
);

create table if not exists public.hierarchy_supersetores (
    setorfilho text primary key,
    supersetor text not null,
    lidermat text default '' not null,
    sort_order integer default 0 not null,
    updated_at timestamptz default now() not null
);

create table if not exists public.hierarchy_subsetores (
    subsetor text primary key,
    setorpai text not null,
    lidermat text default '' not null,
    sort_order integer default 0 not null,
    updated_at timestamptz default now() not null
);

create table if not exists public.kalk_bo_configs (
    scope_type text not null,
    scope_key text not null,
    setor text default '' not null,
    subsetor text default '' not null,
    driver_label text default '' not null,
    indicator_label text default '' not null,
    yellow_min numeric default 3.5 not null,
    green_min numeric default 4.5 not null,
    updated_at timestamptz default now() not null,
    primary key (scope_type, scope_key)
);

create table if not exists public.kalk_bo_values (
    scope_type text not null,
    scope_key text not null,
    mat text not null,
    driver_value numeric,
    indicator_value numeric,
    updated_at timestamptz default now() not null,
    primary key (scope_type, scope_key, mat)
);

alter table public.colaboradores enable row level security;
alter table public.hierarchy_setores enable row level security;
alter table public.hierarchy_supersetores enable row level security;
alter table public.hierarchy_subsetores enable row level security;
alter table public.kalk_bo_configs enable row level security;
alter table public.kalk_bo_values enable row level security;

-- Sem policies: anon/authenticated nao acessam as tabelas diretamente.
-- O app Streamlit usa SUPABASE_SERVICE_ROLE_KEY no backend, que bypassa RLS.
do $$
begin
    if not exists (
        select 1
        from pg_proc p
        join pg_namespace n on n.oid = p.pronamespace
        where n.nspname = 'public'
          and p.proname = 'set_updated_at'
    ) then
        execute $function$
            create function public.set_updated_at()
            returns trigger
            language plpgsql
            as $body$
            begin
                new.updated_at = now();
                return new;
            end;
            $body$
        $function$;
    end if;
end;
$$;

do $$
begin
    if not exists (select 1 from pg_trigger where tgname = 'colaboradores_set_updated_at') then
        create trigger colaboradores_set_updated_at
        before update on public.colaboradores
        for each row execute function public.set_updated_at();
    end if;
end;
$$;

do $$
begin
    if not exists (select 1 from pg_trigger where tgname = 'hierarchy_setores_set_updated_at') then
        create trigger hierarchy_setores_set_updated_at
        before update on public.hierarchy_setores
        for each row execute function public.set_updated_at();
    end if;
end;
$$;

do $$
begin
    if not exists (select 1 from pg_trigger where tgname = 'hierarchy_supersetores_set_updated_at') then
        create trigger hierarchy_supersetores_set_updated_at
        before update on public.hierarchy_supersetores
        for each row execute function public.set_updated_at();
    end if;
end;
$$;

do $$
begin
    if not exists (select 1 from pg_trigger where tgname = 'hierarchy_subsetores_set_updated_at') then
        create trigger hierarchy_subsetores_set_updated_at
        before update on public.hierarchy_subsetores
        for each row execute function public.set_updated_at();
    end if;
end;
$$;

do $$
begin
    if not exists (select 1 from pg_trigger where tgname = 'kalk_bo_configs_set_updated_at') then
        create trigger kalk_bo_configs_set_updated_at
        before update on public.kalk_bo_configs
        for each row execute function public.set_updated_at();
    end if;
end;
$$;

do $$
begin
    if not exists (select 1 from pg_trigger where tgname = 'kalk_bo_values_set_updated_at') then
        create trigger kalk_bo_values_set_updated_at
        before update on public.kalk_bo_values
        for each row execute function public.set_updated_at();
    end if;
end;
$$;
