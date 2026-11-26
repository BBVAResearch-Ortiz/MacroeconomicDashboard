# Respuestas al impulso de Model1002 (DSGE.jl, Fed de Nueva York) para el simulador
# de la ficha «DSGE FRB-NY» del monitor de Estados Unidos.
#
# Escribe dsge_irf.json: respuesta de cada variable (desviación trimestral, en %)
# a un shock de +1 desviación típica. El modelo es lineal, así que la página
# escala y suma estas respuestas según los deslizadores.
#
# Solo hay que volver a ejecutarlo si cambian el modelo o sus parámetros:
#
#   julia --project=. -e 'using Pkg; Pkg.add([
#       PackageSpec(url="https://github.com/FRBNY-DSGE/ModelConstructors.jl"),
#       PackageSpec(url="https://github.com/FRBNY-DSGE/StateSpaceRoutines.jl"),
#       PackageSpec(url="https://github.com/FRBNY-DSGE/SMC.jl"),
#       PackageSpec(url="https://github.com/FRBNY-DSGE/DSGE.jl", rev="main")])'
#   julia --project=. dsge_irf.jl
#
# Probado con Julia 1.10. Las versiones registradas de estos paquetes no se
# instalan en Julia reciente; por eso se toman de los repositorios de la Fed.

using DSGE, ModelConstructors, Dates, Printf

subspec = "ss10"   # especificación estándar de Model1002, con los parámetros por defecto del paquete
horizon = 24

m = Model1002(subspec)
system = compute_system(m)
_, obs, pseudo = impulse_responses(system, horizon; flip_shocks = true)   # +1 desviación típica

exo, o, p = m.exogenous_shocks, m.observables, m.pseudo_observables

# variable => (matriz, fila). Todas en % trimestral.
series = [
    "core_pce_q" => (obs, o[:obs_corepce]),      # inflación PCE subyacente
    "ffr_q"      => (obs, o[:obs_nominalrate]),  # tipo de los fondos federales
    "gdp_q"      => (obs, o[:obs_gdp]),          # crecimiento del PIB
    "rstar_q"    => (pseudo, p[:NaturalRate]),   # tipo de interés natural real
    "spread_q"   => (obs, o[:obs_spread]),       # diferencial Baa–Tesoro
]

# id => (símbolo, nombre ES, nombre EN, signo, variable propia, unidad de la variable propia)
# El signo de b_sh se invierte para que un valor positivo signifique mayor prima de riesgo.
shocks = [
    "monetary"      => (:rm_sh,   "Política monetaria",     "Monetary policy",     1, "ffr_q",      "bp"),
    "productivity"  => (:ztil_sh, "Productividad",          "Productivity",        1, "gdp_q",      "pp"),
    "risk_premium"  => (:b_sh,    "Prima de riesgo",        "Risk premium",       -1, "spread_q",   "bp"),
    "credit_spread" => (:σ_ω_sh,  "Diferencial de crédito", "Credit spread",       1, "spread_q",   "bp"),
    "price_markup"  => (:λ_f_sh,  "Márgenes de precios",    "Price markups",       1, "core_pce_q", "pp"),
    "government"    => (:g_sh,    "Gasto público",          "Government spending", 1, "gdp_q",      "pp"),
]

num(x) = (y = round(x; digits = 5); y == 0 ? "0.0" : string(y))
str(x) = "\"" * x * "\""

parameters = [:ψ1, :ψ2, :ψ3, :ρ, :ζ_p, :ζ_w, :σ_c, :h, :α]

open("dsge_irf.json", "w") do io
    print(io, "{\"model\":\"Model1002\",\"subspec\":", str(subspec),
          ",\"package\":", str("DSGE.jl " * string(pkgversion(DSGE))),
          ",\"repository\":\"https://github.com/FRBNY-DSGE/DSGE.jl\"",
          ",\"computed\":", str(string(today())), ",\"horizon\":", horizon,
          ",\"unit\":\"one standard deviation; quarterly percent deviations\",\"parameters\":{",
          join([str(String(n)) * ":" * num(m[n].value) for n in parameters], ","), "},\"shocks\":{")
    for (i, (id, (symbol, es, en, sign, own, own_unit))) in enumerate(shocks)
        j = exo[symbol]
        print(io, i > 1 ? "," : "", str(id), ":{\"symbol\":", str(String(symbol)), ",\"es\":", str(es), ",\"en\":", str(en),
              ",\"std\":", num(sqrt(system[:QQ][j, j])), ",\"sign\":", sign, ",\"own\":", str(own), ",\"own_unit\":", str(own_unit),
              ",\"responses\":{")
        print(io, join([str(name) * ":[" * join(num.(sign .* arr[row, :, j]), ",") * "]" for (name, (arr, row)) in series], ","))
        print(io, "}}")
    end
    println(io, "}}")
end
println("dsge_irf.json escrito")
