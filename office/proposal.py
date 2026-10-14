from factory.policy import value
from factory.crm import PRICING
from office.store import now


def proposal(card,report):
    name = value(card["config"]["brand"]["name"])
    recipient = value(card["config"]["contact"]["email"])
    link = {"ru":"[Закрытая ссылка на персональное демо — подключить перед отправкой]",
            "en":"[Private personal demo link — connect before sending]",
            "hy":"[Անձնական ցուցադրության փակ հղում՝ միացնել նախքան ուղարկելը]"}[card["language"]]
    p,q = PRICING["standard"],PRICING["installments"]
    bodies = {
        "ru":f"Здравствуйте, команда {name}!\n\nМы изучили информацию о вашей клинике и подготовили предварительную версию сайта специально для вас.\n\n{link}\n\nПосле согласования демо завершим сайт с учётом ваших пожеланий.\n\nВариант 1 — ${p['total']}: ${p['after_demo_and_contract']} после одобрения персонального демо и оформления договора; ${p['at_handover']} при окончательной сдаче сайта.\n\nВариант 2 — ${q['total']} в рассрочку: ${q['after_demo_and_contract']} после одобрения демо и оформления договора; ${q['at_handover']} при сдаче сайта; ещё шесть ежемесячных платежей по $100.\n\nДополнительно: SEO в Армении — $100–500 в месяц; международное SEO — от $500 в месяц.\n\nХостинг и доменное имя оплачиваются отдельно по фактической стоимости выбранного провайдера. Стоимость предварительно согласуем; после оплаты предоставим чек или квитанцию провайдера. Скрытых наценок нет.\n\nКакие пожелания вы хотели бы учесть?\n\nOrder & Profit",
        "en":f"Hello, {name} team!\n\nWe reviewed information about your clinic and prepared a preliminary website specifically for you.\n\n{link}\n\nAfter you approve the demo, we can complete the website with your preferences.\n\nOption 1 — ${p['total']}: ${p['after_demo_and_contract']} after approval of the personal demo and signing the contract; ${p['at_handover']} at final delivery.\n\nOption 2 — ${q['total']} in installments: ${q['after_demo_and_contract']} after demo approval and signing the contract; ${q['at_handover']} at delivery; six further monthly payments of $100.\n\nOptional SEO: Armenia — $100–500 per month; international SEO — from $500 per month.\n\nHosting and domain are charged separately at the chosen provider's actual cost, agreed in advance. We provide the provider's receipt after payment, with no hidden markup.\n\nWhat would you like us to adjust?\n\nOrder & Profit",
        "hy":f"Բարև, {name} թիմ։\n\nՄենք ուսումնասիրել ենք ձեր կլինիկայի մասին տեղեկությունները և հատուկ ձեզ համար պատրաստել կայքի նախնական տարբերակը։\n\n{link}\n\nՑուցադրությունը հաստատելուց հետո կավարտենք կայքը՝ հաշվի առնելով ձեր ցանկությունները։\n\nՏարբերակ 1՝ ${p['total']}․ ${p['after_demo_and_contract']}՝ անհատական ցուցադրությունը հաստատելուց և պայմանագիրը կնքելուց հետո, ${p['at_handover']}՝ կայքի վերջնական հանձնումից հետո։\n\nՏարբերակ 2՝ ${q['total']} ապառիկ․ ${q['after_demo_and_contract']}՝ ցուցադրությունը հաստատելուց և պայմանագիրը կնքելուց հետո, ${q['at_handover']}՝ կայքը հանձնելիս, ևս վեց ամսական վճարում՝ յուրաքանչյուրը $100։\n\nԼրացուցիչ SEO Հայաստանում՝ ամսական $100–500, միջազգային SEO՝ ամսական $500-ից։\n\nՀոսթինգը և դոմենը վճարվում են առանձին՝ ընտրված մատակարարի փաստացի գնով։ Գինը նախապես համաձայնեցվում է, վճարումից հետո տրամադրվում է մատակարարի անդորրագիրը։ Թաքնված հավելավճար չկա։\n\nԻ՞նչ ցանկություններ կուզենայիք հաշվի առնել։\n\nOrder & Profit"}
    return {"to":recipient,"subject":{"ru":f"Персональный сайт для {name}","en":f"A personal website for {name}","hy":f"Անհատական կայք՝ {name}-ի համար"}[card["language"]],
            "body":bodies[card["language"]],"language":card["language"],"buildId":report["buildId"],"revision":card["revision"],
            "createdAt":now(),"delivery":"NOT_SENT","synthetic":card["synthetic"],"sendEnabled":False,
            "blockers":["SENDING_DISABLED","PRIVATE_CLIENT_LINK_NOT_CONNECTED","OWNER_MESSAGE_REVIEW_REQUIRED"]+([] if recipient else ["RECIPIENT_UNVERIFIED"])}
