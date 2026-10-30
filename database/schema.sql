--
-- PostgreSQL database dump
--

\restrict 3UOYGr61iEKZsrNrdhUdVCyZwDVGmFINC2d9xm3eEPaJYCg9qIHgWhOAWaHt89r

-- Dumped from database version 18.4
-- Dumped by pg_dump version 18.4

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: approvaldecision; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.approvaldecision AS ENUM (
    'APPROVED',
    'REJECTED'
);


ALTER TYPE public.approvaldecision OWNER TO postgres;

--
-- Name: memberrole; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.memberrole AS ENUM (
    'ORG_ADMIN',
    'FINANCE_MANAGER',
    'SIGNER',
    'AUDITOR',
    'SYSTEM_OPERATOR'
);


ALTER TYPE public.memberrole OWNER TO postgres;

--
-- Name: proposalstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.proposalstatus AS ENUM (
    'PENDING',
    'APPROVED',
    'REJECTED',
    'FINALIZED',
    'BROADCAST',
    'CONFIRMED'
);


ALTER TYPE public.proposalstatus OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: approvals; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.approvals (
    id integer NOT NULL,
    proposal_id integer NOT NULL,
    signer_id integer NOT NULL,
    decision public.approvaldecision NOT NULL,
    signature_reference character varying(255),
    signature_data text,
    rejection_reason text,
    created_at timestamp with time zone
);


ALTER TABLE public.approvals OWNER TO postgres;

--
-- Name: approvals_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.approvals_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.approvals_id_seq OWNER TO postgres;

--
-- Name: approvals_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.approvals_id_seq OWNED BY public.approvals.id;


--
-- Name: audit_events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.audit_events (
    id integer NOT NULL,
    organization_id integer NOT NULL,
    actor_id integer,
    event_type character varying(100) NOT NULL,
    reference_type character varying(50),
    reference_id character varying(100),
    details json,
    ip_address character varying(45),
    created_at timestamp with time zone
);


ALTER TABLE public.audit_events OWNER TO postgres;

--
-- Name: audit_events_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.audit_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.audit_events_id_seq OWNER TO postgres;

--
-- Name: audit_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.audit_events_id_seq OWNED BY public.audit_events.id;


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.notifications (
    id integer NOT NULL,
    user_id integer NOT NULL,
    title character varying(200) NOT NULL,
    message text NOT NULL,
    category character varying(50),
    read_status boolean,
    created_at timestamp with time zone
);


ALTER TABLE public.notifications OWNER TO postgres;

--
-- Name: notifications_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.notifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.notifications_id_seq OWNER TO postgres;

--
-- Name: notifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.notifications_id_seq OWNED BY public.notifications.id;


--
-- Name: organization_members; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.organization_members (
    id integer NOT NULL,
    organization_id integer NOT NULL,
    user_id integer NOT NULL,
    role public.memberrole NOT NULL,
    created_at timestamp with time zone
);


ALTER TABLE public.organization_members OWNER TO postgres;

--
-- Name: organization_members_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.organization_members_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.organization_members_id_seq OWNER TO postgres;

--
-- Name: organization_members_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.organization_members_id_seq OWNED BY public.organization_members.id;


--
-- Name: organizations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.organizations (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    status character varying(50),
    created_at timestamp with time zone,
    updated_at timestamp with time zone
);


ALTER TABLE public.organizations OWNER TO postgres;

--
-- Name: organizations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.organizations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.organizations_id_seq OWNER TO postgres;

--
-- Name: organizations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.organizations_id_seq OWNED BY public.organizations.id;


--
-- Name: psbt_records; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.psbt_records (
    id integer NOT NULL,
    proposal_id integer NOT NULL,
    unsigned_psbt text NOT NULL,
    current_psbt text NOT NULL,
    finalized_tx_hex text,
    created_at timestamp with time zone,
    updated_at timestamp with time zone
);


ALTER TABLE public.psbt_records OWNER TO postgres;

--
-- Name: psbt_records_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.psbt_records_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.psbt_records_id_seq OWNER TO postgres;

--
-- Name: psbt_records_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.psbt_records_id_seq OWNED BY public.psbt_records.id;


--
-- Name: signer_profiles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.signer_profiles (
    id integer NOT NULL,
    user_id integer NOT NULL,
    label character varying(100) NOT NULL,
    public_key character varying(130) NOT NULL,
    fingerprint character varying(8),
    derivation_path character varying(100),
    status character varying(50),
    created_at timestamp with time zone
);


ALTER TABLE public.signer_profiles OWNER TO postgres;

--
-- Name: signer_profiles_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.signer_profiles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.signer_profiles_id_seq OWNER TO postgres;

--
-- Name: signer_profiles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.signer_profiles_id_seq OWNED BY public.signer_profiles.id;


--
-- Name: spending_policies; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.spending_policies (
    id integer NOT NULL,
    organization_id integer NOT NULL,
    per_transaction_limit bigint,
    daily_limit bigint,
    require_admin_override boolean,
    is_active boolean,
    created_at timestamp with time zone,
    updated_at timestamp with time zone
);


ALTER TABLE public.spending_policies OWNER TO postgres;

--
-- Name: spending_policies_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.spending_policies_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.spending_policies_id_seq OWNER TO postgres;

--
-- Name: spending_policies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.spending_policies_id_seq OWNED BY public.spending_policies.id;


--
-- Name: transaction_proposals; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.transaction_proposals (
    id integer NOT NULL,
    wallet_id integer NOT NULL,
    proposer_id integer NOT NULL,
    destination character varying(100) NOT NULL,
    amount bigint NOT NULL,
    fee_satoshis bigint,
    description text NOT NULL,
    status public.proposalstatus,
    txid character varying(64),
    broadcast_at timestamp with time zone,
    confirmations integer,
    created_at timestamp with time zone,
    updated_at timestamp with time zone
);


ALTER TABLE public.transaction_proposals OWNER TO postgres;

--
-- Name: transaction_proposals_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.transaction_proposals_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.transaction_proposals_id_seq OWNER TO postgres;

--
-- Name: transaction_proposals_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.transaction_proposals_id_seq OWNED BY public.transaction_proposals.id;


--
-- Name: treasury_signers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.treasury_signers (
    id integer NOT NULL,
    wallet_id integer NOT NULL,
    signer_id integer NOT NULL,
    signer_order integer
);


ALTER TABLE public.treasury_signers OWNER TO postgres;

--
-- Name: treasury_signers_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.treasury_signers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.treasury_signers_id_seq OWNER TO postgres;

--
-- Name: treasury_signers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.treasury_signers_id_seq OWNED BY public.treasury_signers.id;


--
-- Name: treasury_wallets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.treasury_wallets (
    id integer NOT NULL,
    organization_id integer NOT NULL,
    wallet_name character varying(100) NOT NULL,
    address character varying(100) NOT NULL,
    redeem_script text,
    descriptor text,
    threshold integer NOT NULL,
    total_signers integer NOT NULL,
    network character varying(20),
    balance_satoshis bigint,
    status character varying(50),
    created_at timestamp with time zone
);


ALTER TABLE public.treasury_wallets OWNER TO postgres;

--
-- Name: treasury_wallets_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.treasury_wallets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.treasury_wallets_id_seq OWNER TO postgres;

--
-- Name: treasury_wallets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.treasury_wallets_id_seq OWNED BY public.treasury_wallets.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    full_name character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    status character varying(50),
    created_at timestamp with time zone,
    updated_at timestamp with time zone
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: approvals id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.approvals ALTER COLUMN id SET DEFAULT nextval('public.approvals_id_seq'::regclass);


--
-- Name: audit_events id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_events ALTER COLUMN id SET DEFAULT nextval('public.audit_events_id_seq'::regclass);


--
-- Name: notifications id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications ALTER COLUMN id SET DEFAULT nextval('public.notifications_id_seq'::regclass);


--
-- Name: organization_members id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.organization_members ALTER COLUMN id SET DEFAULT nextval('public.organization_members_id_seq'::regclass);


--
-- Name: organizations id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.organizations ALTER COLUMN id SET DEFAULT nextval('public.organizations_id_seq'::regclass);


--
-- Name: psbt_records id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.psbt_records ALTER COLUMN id SET DEFAULT nextval('public.psbt_records_id_seq'::regclass);


--
-- Name: signer_profiles id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.signer_profiles ALTER COLUMN id SET DEFAULT nextval('public.signer_profiles_id_seq'::regclass);


--
-- Name: spending_policies id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.spending_policies ALTER COLUMN id SET DEFAULT nextval('public.spending_policies_id_seq'::regclass);


--
-- Name: transaction_proposals id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transaction_proposals ALTER COLUMN id SET DEFAULT nextval('public.transaction_proposals_id_seq'::regclass);


--
-- Name: treasury_signers id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.treasury_signers ALTER COLUMN id SET DEFAULT nextval('public.treasury_signers_id_seq'::regclass);


--
-- Name: treasury_wallets id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.treasury_wallets ALTER COLUMN id SET DEFAULT nextval('public.treasury_wallets_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: approvals approvals_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.approvals
    ADD CONSTRAINT approvals_pkey PRIMARY KEY (id);


--
-- Name: audit_events audit_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_events
    ADD CONSTRAINT audit_events_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: organization_members organization_members_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.organization_members
    ADD CONSTRAINT organization_members_pkey PRIMARY KEY (id);


--
-- Name: organizations organizations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_pkey PRIMARY KEY (id);


--
-- Name: psbt_records psbt_records_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.psbt_records
    ADD CONSTRAINT psbt_records_pkey PRIMARY KEY (id);


--
-- Name: psbt_records psbt_records_proposal_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.psbt_records
    ADD CONSTRAINT psbt_records_proposal_id_key UNIQUE (proposal_id);


--
-- Name: signer_profiles signer_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.signer_profiles
    ADD CONSTRAINT signer_profiles_pkey PRIMARY KEY (id);


--
-- Name: spending_policies spending_policies_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.spending_policies
    ADD CONSTRAINT spending_policies_pkey PRIMARY KEY (id);


--
-- Name: transaction_proposals transaction_proposals_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transaction_proposals
    ADD CONSTRAINT transaction_proposals_pkey PRIMARY KEY (id);


--
-- Name: treasury_signers treasury_signers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.treasury_signers
    ADD CONSTRAINT treasury_signers_pkey PRIMARY KEY (id);


--
-- Name: treasury_wallets treasury_wallets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.treasury_wallets
    ADD CONSTRAINT treasury_wallets_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_approvals_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_approvals_id ON public.approvals USING btree (id);


--
-- Name: ix_audit_events_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_audit_events_id ON public.audit_events USING btree (id);


--
-- Name: ix_notifications_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_notifications_id ON public.notifications USING btree (id);


--
-- Name: ix_organization_members_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_organization_members_id ON public.organization_members USING btree (id);


--
-- Name: ix_organizations_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_organizations_id ON public.organizations USING btree (id);


--
-- Name: ix_psbt_records_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_psbt_records_id ON public.psbt_records USING btree (id);


--
-- Name: ix_signer_profiles_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_signer_profiles_id ON public.signer_profiles USING btree (id);


--
-- Name: ix_spending_policies_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_spending_policies_id ON public.spending_policies USING btree (id);


--
-- Name: ix_transaction_proposals_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_transaction_proposals_id ON public.transaction_proposals USING btree (id);


--
-- Name: ix_transaction_proposals_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_transaction_proposals_status ON public.transaction_proposals USING btree (status);


--
-- Name: ix_transaction_proposals_txid; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_transaction_proposals_txid ON public.transaction_proposals USING btree (txid);


--
-- Name: ix_treasury_signers_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_treasury_signers_id ON public.treasury_signers USING btree (id);


--
-- Name: ix_treasury_wallets_address; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_treasury_wallets_address ON public.treasury_wallets USING btree (address);


--
-- Name: ix_treasury_wallets_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_treasury_wallets_id ON public.treasury_wallets USING btree (id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: approvals approvals_proposal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.approvals
    ADD CONSTRAINT approvals_proposal_id_fkey FOREIGN KEY (proposal_id) REFERENCES public.transaction_proposals(id) ON DELETE CASCADE;


--
-- Name: approvals approvals_signer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.approvals
    ADD CONSTRAINT approvals_signer_id_fkey FOREIGN KEY (signer_id) REFERENCES public.signer_profiles(id) ON DELETE CASCADE;


--
-- Name: audit_events audit_events_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_events
    ADD CONSTRAINT audit_events_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.users(id);


--
-- Name: audit_events audit_events_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_events
    ADD CONSTRAINT audit_events_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: organization_members organization_members_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.organization_members
    ADD CONSTRAINT organization_members_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: organization_members organization_members_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.organization_members
    ADD CONSTRAINT organization_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: psbt_records psbt_records_proposal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.psbt_records
    ADD CONSTRAINT psbt_records_proposal_id_fkey FOREIGN KEY (proposal_id) REFERENCES public.transaction_proposals(id) ON DELETE CASCADE;


--
-- Name: signer_profiles signer_profiles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.signer_profiles
    ADD CONSTRAINT signer_profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: spending_policies spending_policies_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.spending_policies
    ADD CONSTRAINT spending_policies_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: transaction_proposals transaction_proposals_proposer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transaction_proposals
    ADD CONSTRAINT transaction_proposals_proposer_id_fkey FOREIGN KEY (proposer_id) REFERENCES public.users(id);


--
-- Name: transaction_proposals transaction_proposals_wallet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transaction_proposals
    ADD CONSTRAINT transaction_proposals_wallet_id_fkey FOREIGN KEY (wallet_id) REFERENCES public.treasury_wallets(id) ON DELETE CASCADE;


--
-- Name: treasury_signers treasury_signers_signer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.treasury_signers
    ADD CONSTRAINT treasury_signers_signer_id_fkey FOREIGN KEY (signer_id) REFERENCES public.signer_profiles(id) ON DELETE CASCADE;


--
-- Name: treasury_signers treasury_signers_wallet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.treasury_signers
    ADD CONSTRAINT treasury_signers_wallet_id_fkey FOREIGN KEY (wallet_id) REFERENCES public.treasury_wallets(id) ON DELETE CASCADE;


--
-- Name: treasury_wallets treasury_wallets_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.treasury_wallets
    ADD CONSTRAINT treasury_wallets_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict 3UOYGr61iEKZsrNrdhUdVCyZwDVGmFINC2d9xm3eEPaJYCg9qIHgWhOAWaHt89r

