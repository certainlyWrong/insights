<script setup>
import { inject, toRefs } from "vue";
import { ArrowUpRight, Landmark, Percent, ChartNoAxesCombined, CircleDollarSign, ChartColumnIncreasing, HeartHandshake, ReceiptText, ArrowRight, Info } from "@lucide/vue";
import TrendChart from "../components/TrendChart.vue";
import MetricCard from "../components/MetricCard.vue";
import SectionHeading from "../components/SectionHeading.vue";
const { data, debtLatest, latestInterestYear, macroLatest, latestYear, socialLatest, pibLatest, taxLatest, taxAnnualRunning, purchasingPowerLatest, pretty, tri, percent, month, debtChart, macroChart, overviewTrend, chartGuides, go } = toRefs(inject("dashboard"));
</script>

<template>
<section class="content">
          <section class="hero">
            <div class="hero-copy">
              <div class="eyebrow"><span></span> UM RETRATO DOS RECURSOS PÚBLICOS</div>
              <h1 tabindex="-1">O que devemos.<br /><em>O que escolhemos financiar.</em></h1>
              <p>Acompanhe quanto o governo deve, quanto arrecada e como distribui os recursos. Indicadores oficiais mostram séries históricas, métodos e limites de interpretação.</p>
              <button class="hero-link" @click="go('explorer')">Explorar todas as bases <ArrowUpRight class="ui-icon" :size="15" /></button>
            </div>
            <div class="hero-visual" aria-hidden="true">
              <div class="orbit orbit-a"></div><div class="orbit orbit-b"></div><div class="orbit orbit-c"></div>
              <div class="visual-core"><span>BR</span></div>
              <i class="orb-node n1"></i><i class="orb-node n2"></i><i class="orb-node n3"></i>
              <span class="visual-word word-a">DÍVIDA</span><span class="visual-word word-b">ORÇAMENTO</span><span class="visual-word word-c">BRASIL</span>
            </div>
            <div class="hero-range"><span>RECORTE HISTÓRICO</span><strong>1994 <i>—</i> 2026</strong></div>
          </section>

          <SectionHeading kicker="EM NÚMEROS" title="Panorama mais recente" note="Últimos dados disponíveis" />
          <div class="metrics">
            <MetricCard tone="blue"><template #label>ESTOQUE DA DPF <span><ArrowUpRight class="ui-icon" :size="12" :stroke-width="2" /></span></template><template #value>R$ {{ tri(debtLatest?.dpf_bilhoes) }} <small>tri</small></template><template #foot><span>{{ month(debtLatest?.data) }}</span><i>Dívida federal · Tesouro</i></template><template #decoration><div class="sparkline" aria-hidden="true"><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b></div></template></MetricCard>
            <MetricCard tone="red"><template #label>DÍVIDA BRUTA / PIB <span>%</span></template><template #value>{{ percent(macroLatest?.dbgg_percentual_pib) }}</template><template #foot><span>{{ month(macroLatest?.data) }}</span><i>Governo geral · BCB</i></template><template #decoration><div class="sparkline" aria-hidden="true"><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b></div></template></MetricCard>
            <MetricCard tone="gold"><template #label>JUROS APROPRIADOS · ANO COMPLETO</template><template #value>R$ {{ pretty(latestInterestYear?.juros_dpf_bilhoes, 1) }} <small>bi</small></template><template #foot><span>{{ latestInterestYear?.ano }}</span><i>Competência · Tesouro</i></template><template #decoration><div class="sparkline" aria-hidden="true"><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b></div></template></MetricCard>
            <MetricCard tone="teal"><template #label>ARRECADAÇÃO FEDERAL · {{ taxLatest?.ano }}</template><template #value>R$ {{ pretty(taxAnnualRunning / 1e6, 2) }} <small>tri</small></template><template #foot><span>Até {{ month(taxLatest?.data) }}</span><i>Total publicado · RFB</i></template><template #decoration><div class="sparkline" aria-hidden="true"><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b></div></template></MetricCard>
          </div>

          <SectionHeading kicker="EXPLORE OS ESTUDOS" title="Sete perspectivas sobre as contas públicas" note="Indicadores com fontes e método" index-title />
          <div class="overview-links">
            <button @click="go('debt')"><div class="overview-link-head"><Landmark class="overview-topic-icon" :size="16"/><span>DÍVIDA PÚBLICA</span></div><strong>Estoque, composição e fatores</strong><small>DPF · Tesouro Nacional <ArrowUpRight class="ui-icon" :size="12" /></small></button>
            <button @click="go('interest')"><div class="overview-link-head"><Percent class="overview-topic-icon" :size="16"/><span>JUROS</span></div><strong>R$ {{ pretty(latestInterestYear?.juros_dpf_bilhoes, 0) }} bi apropriados em {{ latestInterestYear?.ano }}</strong><small>Competência e custo aproximado <ArrowUpRight class="ui-icon" :size="12" /></small></button>
            <button @click="go('pib')"><div class="overview-link-head"><ChartNoAxesCombined class="overview-topic-icon" :size="16"/><span>ATIVIDADE ECONÔMICA</span></div><strong>PIB real: {{ percent(pibLatest?.pib_yoy_percentual) }} no último trimestre</strong><small>IBGE · Contas Nacionais <ArrowUpRight class="ui-icon" :size="12" /></small></button>
            <button @click="go('purchasingPower')"><div class="overview-link-head"><CircleDollarSign class="overview-topic-icon" :size="16"/><span>PODER DE COMPRA</span></div><strong>O real mantém {{ percent(purchasingPowerLatest?.poder_compra_remanescente_percentual) }} do poder de compra inicial</strong><small>IPCA desde julho de 1994 <ArrowUpRight class="ui-icon" :size="12" /></small></button>
            <button @click="go('spending')"><div class="overview-link-head"><ChartColumnIncreasing class="overview-topic-icon" :size="16"/><span>ORÇAMENTO FEDERAL</span></div><strong>Saúde, educação e segurança</strong><small>Pagamentos e investimento público <ArrowUpRight class="ui-icon" :size="12" /></small></button>
            <button @click="go('social')"><div class="overview-link-head"><HeartHandshake class="overview-topic-icon" :size="16"/><span>PROTEÇÃO SOCIAL</span></div><strong>{{ pretty(socialLatest?.beneficiarios_total, 0) }} pessoas no BPC em {{ socialLatest?.ano }}</strong><small>BPC, Bolsa Família e Auxílio Gás <ArrowUpRight class="ui-icon" :size="12" /></small></button>
            <button @click="go('taxes')"><div class="overview-link-head"><ReceiptText class="overview-topic-icon" :size="16"/><span>ARRECADAÇÃO DE IMPOSTOS</span></div><strong>R$ {{ pretty(taxAnnualRunning / 1e6, 2) }} tri no ano até {{ month(taxLatest?.data) }}</strong><small>Receita federal · sem projeção <ArrowUpRight class="ui-icon" :size="12" /></small></button>
          </div>

          <div class="dashboard-grid">
            <article class="panel panel-debt">
              <div class="panel-heading"><div><span class="kicker">2000 — 2026</span><h3>Trajetória da dívida federal</h3></div><button class="subtle-link" @click="go('debt')">Ver análise <b><ArrowUpRight class="ui-icon" :size="12" :stroke-width="2" /></b></button></div>
              <TrendChart :option="debtChart" :guide="chartGuides.debt" height="360px" />
              <div class="legend-row"><span><i class="legend blue"></i> DPF total</span><span><i class="legend teal"></i> Interna</span><span><i class="legend coral"></i> Externa</span><small>R$ trilhões correntes</small></div>
            </article>
            <article class="panel panel-macro">
              <div class="panel-heading"><div><span class="kicker">BANCO CENTRAL</span><h3>Dívida e tamanho da economia</h3></div><span class="unit-pill">% do PIB</span></div>
              <TrendChart :option="macroChart" :guide="chartGuides.macro" height="310px" />
              <p class="panel-caption">A DBGG inclui também estados e municípios. Seu escopo é mais amplo que a DPF.</p>
            </article>
          </div>
          <SectionHeading kicker="ORÇAMENTO FEDERAL" title="Recursos pagos por área" spacer><button class="subtle-link" @click="go('spending')">Ver saúde, educação e segurança <b><ArrowRight class="ui-icon" :size="12" :stroke-width="2" /></b></button></SectionHeading>
          <article class="panel">
            <div class="panel-heading"><div><span class="kicker">2001 — {{ latestYear }} · VALORES REAIS</span><h3>Gasto federal corrigido pela inflação</h3></div><span class="unit-pill">IPCA · R$ de 2025</span></div>
            <TrendChart :option="overviewTrend" :guide="chartGuides.spending" height="345px" />
            <div class="legend-row"><span><i class="legend coral"></i> Saúde</span><span><i class="legend teal"></i> Educação</span><span><i class="legend gold"></i> Segurança Pública</span><small>Valores corrigidos pelo IPCA</small></div>
          </article>
          <SectionHeading kicker="PROTEÇÃO SOCIAL" title="Programas de grande escala" spacer><button class="subtle-link" @click="go('social')">Ver série e método <b><ArrowRight class="ui-icon" :size="12" :stroke-width="2" /></b></button></SectionHeading>
          <div class="spending-cards"><article class="spend-card education-card"><span>BPC · BENEFICIÁRIOS · {{ socialLatest?.ano }}</span><strong>{{ pretty(socialLatest?.beneficiarios_total, 0) }}</strong><small>R$ {{ pretty(socialLatest?.repasse_total_brl / 1e9, 1) }} bi em repasses nominais</small></article><article class="spend-card health-card"><span>BOLSA FAMÍLIA · 2024</span><strong>R$ 168,3 bi</strong><small>Mais de 20,86 milhões de famílias alcançadas</small></article><article class="spend-card security-card"><span>AUXÍLIO GÁS · 2024</span><strong>5,7 mi</strong><small>Famílias por ciclo bimestral em média</small></article></div>
          <aside class="scope-callout"><span><Info class="ui-icon" :size="14" /></span><p><strong>Escopos diferentes, dados complementares.</strong> A DPF mede obrigações federais sob responsabilidade do Tesouro; DBGG/PIB abrange o governo geral. Os gastos por área são da execução orçamentária federal e não incluem despesas próprias de estados e municípios.</p><button @click="go('sources')">Entenda o método <b><ArrowRight class="ui-icon" :size="12" :stroke-width="2" /></b></button></aside>
        </section>
</template>
